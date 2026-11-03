"""Folder scanning, validated destinations, previewed operations and crash-aware undo."""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable

from .extractors import get_text
from .taxonomy import CATEGORY_TREE, classify, explain_classification
from .vocabulary import Vocabulary, valid_category

SKIP_DIRS = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv",
             "$recycle.bin", "system volume information", "windows", "program files",
             "program files (x86)", "programdata", "appdata", "site-packages", ".sortiq"}


def app_data_dir() -> Path:
    home = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    folder = Path(home) / "SORTIQ" if home else Path.home() / ".sortiq"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def default_library() -> Path:
    documents = Path.home() / "Documents"
    return (documents if documents.is_dir() else Path.home()) / "SORTIQ Library"


def inside(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (ValueError, OSError, RuntimeError):
        return False


@dataclass
class Suggestion:
    source: Path
    category: str
    confidence: float
    reason: str
    size: int
    status: str = "Ready"
    excerpt: str = ""
    error: str = ""
    manually_set: bool = False
    explanation: str = ""
    mtime_ns: int = 0

    @property
    def display_confidence(self) -> str:
        return "Manual" if self.manually_set else f"{round(self.confidence * 100)}%"


def override(suggestion: Suggestion, category: str) -> Suggestion:
    if category not in CATEGORY_TREE:
        raise ValueError("Unknown destination category")
    return replace(suggestion, category=category, confidence=1.0 if category != "Needs Review" else 0.0,
                   status="Ready" if category != "Needs Review" else "Review", reason="Manual category selected",
                   manually_set=True)


def _hidden_or_system(path: Path) -> bool:
    # Windows Explorer hidden/system and reparse-point checks; skip if inaccessible.
    try:
        flags = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        return bool(flags & (getattr(stat,"FILE_ATTRIBUTE_HIDDEN",2) |
                             getattr(stat,"FILE_ATTRIBUTE_SYSTEM",4) |
                             getattr(stat,"FILE_ATTRIBUTE_REPARSE_POINT",1024)))
    except OSError:
        return True


def iter_files(roots: Iterable[Path], destination: Path, recursive: bool = True,
               cancel: threading.Event | None = None):
    """Never follow directory symlinks or include the destination library in a scan."""
    seen = set()
    for requested in roots:
        root = Path(requested).expanduser().resolve()
        if not root.is_dir() or inside(root, destination) or _hidden_or_system(root):
            continue
        if os.name == "nt":
            # Never scan Windows, Program Files or ProgramData, even when a
            # protected location is selected indirectly. Do not reject a
            # user's selected folder merely because an ancestor is AppData:
            # Windows temp directories and many legitimate user folders live
            # there (and CI test folders do as well).
            protected = (os.environ.get("WINDIR"), os.environ.get("ProgramFiles"),
                         os.environ.get("ProgramFiles(x86)"), os.environ.get("PROGRAMDATA"))
            if root == Path(root.anchor) or any(inside(root, Path(p)) for p in protected if p):
                continue
        for parent, dirs, files in os.walk(root, followlinks=False):
            if cancel is not None and cancel.is_set():
                return
            cur = Path(parent)
            dirs[:] = [d for d in dirs if not d.startswith(".") and d.casefold() not in SKIP_DIRS
                       and not (cur / d).is_symlink() and not _hidden_or_system(cur / d)
                       and not inside(cur / d, destination)] if recursive else []
            for filename in files:
                if filename.startswith("~$") or filename.startswith("."):
                    continue
                path = cur / filename
                if path.is_symlink() or _hidden_or_system(path) or inside(path, destination):
                    continue
                ident = str(path.resolve()).casefold()
                if ident in seen:
                    continue
                seen.add(ident)
                if path.is_file():
                    yield path


def scan(roots: Iterable[Path], destination: Path, read_contents: bool = True,
         recursive: bool = True, progress: Callable[[int, str], None] | None = None,
         cancel: threading.Event | None = None, max_files: int = 35_000, vocabulary: Vocabulary | None = None) -> list[Suggestion]:
    rows: list[Suggestion] = []
    for path in iter_files(roots, destination, recursive=recursive, cancel=cancel):
        if cancel is not None and cancel.is_set():
            break
        if len(rows) >= max_files:
            raise RuntimeError(f"Scan limit of {max_files:,} files reached. Select smaller folders.")
        try:
            size = path.stat().st_size
            # Avoid expensive parsing of gigantic files. Filename classification still works.
            text, parser_note = get_text(path) if read_contents and size <= 55 * 1024 * 1024 else ("", None)
            smart = vocabulary.classify(path.name, str(path.parent), text) if vocabulary else None
            classification = classify(path.name, str(path.parent), text) if smart is None else None
            status = smart[2] if smart else ("Review" if classification.category == "Needs Review" or classification.confidence < 0.60 else "Ready")
            if parser_note:
                reason = (smart[3] if smart else classification.reason) + f" · {parser_note}"
            else:
                reason = smart[3] if smart else classification.reason
            rows.append(Suggestion(source=path, category=(smart[0] if smart else classification.category),
                                   confidence=(smart[1] if smart else classification.confidence), reason=reason,
                                   size=size, status=status, excerpt=text[:350], error=parser_note or "",
                                   explanation=(smart[4] if smart else explain_classification(path.name, str(path.parent), text, classification))))
        except (OSError, PermissionError) as e:
            rows.append(Suggestion(source=path, category="Needs Review", confidence=0.0,
                                   reason=f"Cannot inspect: {e}", size=0, status="Review", error=str(e)))
        if progress and len(rows) % 12 == 0:
            progress(len(rows), path.name)
    if progress:
        progress(len(rows), "Complete")
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_category_path(category: str) -> Path:
    valid_category(category)
    if category not in CATEGORY_TREE or category == "Needs Review":
        raise ValueError("Choose a specific category; Needs Review cannot be filed")
    parts = tuple(part.strip() for part in category.split(" / "))
    if any(p in (".", "..", "") or any(ch in p for ch in r'<>:"\\|?*') for p in parts):
        raise ValueError("Invalid folder name")
    return Path(*parts)


def proposed_destination(root: Path, suggestion: Suggestion) -> Path:
    return Path(root).expanduser().resolve() / validate_category_path(suggestion.category) / suggestion.source.name


class History:
    """Each operation is written as pending before touching a file; recovery repairs interrupted writes."""
    def __init__(self, db_path: Path | None = None):
        self.db_path = Path(db_path or app_data_dir() / "history.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                source TEXT NOT NULL,
                dest TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('move', 'copy')),
                digest TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                message TEXT NOT NULL DEFAULT ''
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_batch ON operations(batch_id, id)")
        self.recover()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=15)

    def pending(self, batch_id: str, source: Path, dest: Path, mode: str, digest: str) -> int:
        with self._connect() as db:
            cur = db.execute("INSERT INTO operations(batch_id, source, dest, mode, digest, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                             (batch_id, str(source), str(dest), mode, digest, time.time()))
            return int(cur.lastrowid)

    def mark(self, operation_id: int, status: str, message: str = "") -> None:
        with self._connect() as db:
            db.execute("UPDATE operations SET status=?, message=? WHERE id=?", (status, message, operation_id))

    def recover(self) -> None:
        with self._connect() as db:
            rows = db.execute("SELECT id, source, dest, mode, digest FROM operations WHERE status='pending'").fetchall()
        for op_id, src, dst, mode, digest in rows:
            source, dest = Path(src), Path(dst)
            try:
                if dest.is_file() and sha256(dest) == digest and (mode == "copy" or not source.exists()):
                    self.mark(op_id, "done", "Recovered after interrupted operation")
                else:
                    self.mark(op_id, "failed", "Interrupted or source/destination state ambiguous")
            except OSError:
                self.mark(op_id, "failed", "Unable to verify interrupted operation")

    def last_batch(self) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT batch_id FROM operations WHERE status IN ('done','undo_failed') ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def items_for_batch(self, batch_id: str) -> list[tuple]:
        with self._connect() as db:
            return db.execute("SELECT id, source, dest, mode, digest, status FROM operations WHERE batch_id=? ORDER BY id DESC", (batch_id,)).fetchall()

    def recent(self, limit: int = 200) -> list[tuple]:
        with self._connect() as db:
            return db.execute("SELECT created_at, source, dest, mode, status, message FROM operations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


@dataclass
class SortResult:
    batch_id: str
    sorted: int = 0
    duplicates: int = 0
    skipped: int = 0
    failures: tuple[str, ...] = ()


def choose_destination(planned: Path, origin: Path, digest: str) -> tuple[Path, bool]:
    """Return a unique name or exact-content duplicate. Never overwrite a file."""
    stem, ext = planned.stem, planned.suffix
    for number in range(0, 100_000):
        option = planned if number == 0 else planned.with_name(f"{stem} ({number + 1}){ext}")
        if not option.exists():
            return option, False
        if option.is_file() and option.stat().st_size == origin.stat().st_size and sha256(option) == digest:
            return option, True
    raise RuntimeError("Too many same-name files in destination")


def sort_files(suggestions: Iterable[Suggestion], destination: Path, allowed_roots: Iterable[Path],
               history: History, mode: str = "copy",
               progress: Callable[[int, int, str], None] | None = None) -> SortResult:
    if mode not in ("move", "copy"):
        raise ValueError("Mode must be copy or move")
    dest_root = Path(destination).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in allowed_roots]
    if not roots:
        raise ValueError("Select at least one source folder")
    batch_id = uuid.uuid4().hex
    items = list(suggestions)
    completed = duplicates = skipped = 0
    failures: list[str] = []
    for index, item in enumerate(items, 1):
        try:
            src = item.source.expanduser().resolve(strict=True)
            if not src.is_file() or item.source.is_symlink() or not any(inside(src, root) for root in roots):
                raise ValueError("File is missing, linked or outside selected folders")
            if inside(src, dest_root):
                raise ValueError("Source is already inside the output library")
            if item.category == "Needs Review" or item.status == "Review":
                skipped += 1
                continue
            # Reject stale scan results if file was changed since the scan.
            current_stat = src.stat()
            if current_stat.st_size != item.size or (item.mtime_ns and current_stat.st_mtime_ns != item.mtime_ns):
                raise ValueError("File changed since scan; rescan first")
            digest = sha256(src)
            target, already = choose_destination(proposed_destination(dest_root, item), src, digest)
            if already:
                duplicates += 1
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            op_id = history.pending(batch_id, src, target, mode, digest)
            created_target = False
            try:
                if mode == "copy":
                    # Exclusive create avoids overwrites if another process creates a target.
                    with src.open("rb") as stream, target.open("xb") as output:
                        created_target = True
                        shutil.copyfileobj(stream, output, length=1024 * 1024)
                    shutil.copystat(src, target)
                else:
                    # Move through an exclusive copy first, then unlink the verified source.
                    # This also works across drives (unlike os.rename).
                    with src.open("rb") as stream, target.open("xb") as output:
                        created_target = True
                        shutil.copyfileobj(stream, output, length=1024 * 1024)
                    shutil.copystat(src, target)
                if sha256(target) != digest:
                    raise IOError("Destination verification failed")
                if mode == "move":
                    # Re-verify source before unlink to avoid losing concurrent edits.
                    if sha256(src) != digest:
                        raise IOError("Source changed during move; original preserved")
                    src.unlink()
                history.mark(op_id, "done")
                completed += 1
            except Exception as exc:
                # Never remove an existing file we did not create, even if another
                # program raced to create it after our preview.
                complete_copy = False
                if created_target and target.is_file():
                    try:
                        complete_copy = sha256(target) == digest
                        if not complete_copy:
                            target.unlink()
                    except OSError:
                        pass
                if complete_copy and (mode == "copy" or not src.exists()):
                    # The file operation completed; record it even if a final UI/log step failed.
                    history.mark(op_id, "done", f"Recovered completion: {exc}")
                else:
                    history.mark(op_id, "failed", str(exc))
                raise
        except Exception as exc:
            failures.append(f"{item.source.name}: {exc}")
        finally:
            if progress:
                progress(index, len(items), item.source.name)
    return SortResult(batch_id, completed, duplicates, skipped, tuple(failures))


def undo_last(history: History, progress: Callable[[int, int, str], None] | None = None) -> tuple[int, tuple[str, ...]]:
    batch = history.last_batch()
    if not batch:
        return 0, ()
    operations = [row for row in history.items_for_batch(batch) if row[5] in ("done", "undo_failed")]
    done = 0
    problems: list[str] = []
    for idx, (op_id, original, destination, mode, digest, status) in enumerate(operations, 1):
        src, dst = Path(original), Path(destination)
        try:
            if not dst.is_file() or sha256(dst) != digest:
                raise ValueError("Sorted file is missing or has changed; will not overwrite anything")
            if mode == "move":
                if src.exists():
                    raise FileExistsError("Original location is occupied")
                src.parent.mkdir(parents=True, exist_ok=True)
                # Use copy-verify-unlink for cross-volume restoration.
                with dst.open("rb") as stream, src.open("xb") as output:
                    shutil.copyfileobj(stream, output, length=1024 * 1024)
                shutil.copystat(dst, src)
                if sha256(src) != digest:
                    src.unlink(missing_ok=True)
                    raise IOError("Restoration verification failed; sorted copy kept")
                dst.unlink()
            else:
                dst.unlink()
            history.mark(op_id, "undone")
            done += 1
        except Exception as e:
            history.mark(op_id, "undo_failed", str(e))
            problems.append(f"{dst.name}: {e}")
        if progress:
            progress(idx, len(operations), dst.name)
    return done, tuple(problems)
