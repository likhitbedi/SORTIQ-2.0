"""SORTIQ Classic: compact WinRAR-inspired Tkinter file organizer.

Local-first, deliberate organization: Scan -> Review -> Copy/Move -> Undo.
The engine is shared with SORTIQ V1; this module only replaces the interface.
"""
from __future__ import annotations

import csv
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext

from . import __version__
from .config import load, save
from .engine import History, Suggestion, default_library, inside, override, scan, sort_files, undo_last
from .taxonomy import CATEGORY_TREE
from .vocabulary import Vocabulary
from .subject_ui import SubjectManager
from .autopilot import (AnalysisCache, HybridClassifier, LocalSemanticModel,
                        auto_scan, load_profile, register_profile)
from .onboarding import Onboarding

FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"
BG = "#F0F0F0"
WHITE = "#FFFFFF"
TEXT = "#202020"
GRAY = "#616161"
BLUE = "#DCEBFF"
LINE = "#C9C9C9"


def fmt_size(count: int) -> str:
    value = float(count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


class SortiqApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"SORTIQ Classic  -  File Organizer  v{__version__}")
        self.geometry("1210x720")
        self.minsize(940, 550)
        self.configure(bg=BG)
        self.settings = load()
        from .engine import app_data_dir
        self.vocab_path = app_data_dir() / "vocabulary.json"
        self.vocab = Vocabulary.load(self.vocab_path)
        self.profile = load_profile()
        self._setup_window = None  # Exactly one first-run wizard per application window.
        if self.profile: register_profile(self.profile)
        self.folders: list[str] = [p for p in self.settings.get("folders", []) if Path(p).is_dir()]
        self.rows: list[Suggestion] = []
        self.jobs: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.busy = False
        self.history = History()
        self.destination_var = tk.StringVar(value=self.settings.get("destination", str(default_library())))
        self.read_var = tk.BooleanVar(value=self.settings.get("read_contents", True))
        self.recursive_var = tk.BooleanVar(value=self.settings.get("recursive", True))
        self.mode_var = tk.StringVar(value=self.settings.get("mode", "copy"))
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="All files")
        self.category_var = tk.StringVar(value=CATEGORY_TREE[0])
        self.advanced_var = tk.BooleanVar(value=False)
        self.message_var = tk.StringVar(value="Welcome. Describe your work in AI Setup, then click AI Organize.")
        self.count_var = tk.StringVar(value="0 files")
        self.detail_var = tk.StringVar(value="Select a file to see why SORTIQ suggested its destination.")
        self.nav_paths: dict[str, Path | None] = {}
        self.active_folder: Path | None = None
        self.history_visible = False
        self.sort_key = "file"
        self.sort_reverse = False
        self._load_icons()
        self._style()
        self._build()
        self.search_var.trace_add("write", lambda *_: self.refresh_table())
        self.filter_var.trace_add("write", lambda *_: self.refresh_table())
        self._refresh_folders()
        self.after(120, self._poll_jobs)
        if not self.profile:
            self.after(700, self.setup_assistant)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_icons(self):
        """Keep icons accessible both from source and the packaged PyInstaller build."""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "assets" / "icons"
        names = ("app", "add", "remove", "scan", "organize", "undo", "files", "history",
                 "export", "demo", "why", "folder", "folder-blue", "folder-purple",
                 "folder-gray", "pdf", "ppt", "word", "excel", "archive", "image", "file")
        self.icons = {}
        for name in names:
            try:
                self.icons[name] = tk.PhotoImage(file=str(base / f"{name}.png"))
                self.icons[name + "_small"] = tk.PhotoImage(file=str(base / f"{name}-small.png"))
            except (tk.TclError, OSError):
                pass
        if "app" in self.icons:
            self.iconphoto(True, self.icons["app"])

    def _file_icon(self, file_path: Path):
        ext = file_path.suffix.casefold()
        key = {
            ".pdf":"pdf", ".pptx":"ppt", ".ppt":"ppt", ".docx":"word", ".doc":"word",
            ".xlsx":"excel", ".xls":"excel", ".csv":"excel", ".zip":"archive",
            ".rar":"archive", ".7z":"archive", ".png":"image", ".jpg":"image",
            ".jpeg":"image", ".webp":"image", ".gif":"image",
        }.get(ext,"file")
        return self.icons.get(key + "_small")

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 9))
        style.configure("TButton", background="#EAEAEA", foreground=TEXT, font=(FONT, 9), padding=(9, 6), relief="raised")
        style.map("TButton", background=[("active", "#D9E6F5"), ("disabled", "#F5F5F5")])
        style.configure("TCheckbutton", background=BG, foreground=TEXT, font=(FONT, 9))
        style.configure("TRadiobutton", background=BG, foreground=TEXT, font=(FONT, 9))
        style.configure("TCombobox", fieldbackground=WHITE, padding=(3, 4))
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=TEXT,
                        bordercolor=LINE, borderwidth=1, rowheight=24, font=(FONT, 9))
        style.configure("Treeview.Heading", background="#E8E8E8", foreground=TEXT, borderwidth=1,
                        font=(FONT, 9), relief="raised", padding=(6, 6))
        style.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", TEXT)])
        style.configure("TPanedwindow", background=LINE)

    def _build(self):
        self._menu()
        self._toolbar()
        self._address_bar()
        self._main_area()
        status = tk.Frame(self, bg="#EAEAEA", highlightbackground=LINE, highlightthickness=1)
        status.pack(side="bottom", fill="x")
        tk.Label(status, textvariable=self.message_var, bg="#EAEAEA", fg=TEXT, font=(FONT, 9),
                 anchor="w", padx=10).pack(side="left", fill="x", expand=True, pady=5)
        tk.Label(status, textvariable=self.count_var, bg="#EAEAEA", fg=GRAY, font=(FONT, 9),
                 anchor="e", padx=10).pack(side="right", pady=5)
        self._bottom_bar()
        self.selection_frame.pack_forget()

    def _menu(self):
        bar = tk.Menu(self)
        filemenu = tk.Menu(bar, tearoff=False)
        filemenu.add_command(label="Add source folder...", command=self.add_folder, accelerator="Ctrl+O")
        filemenu.add_command(label="Remove selected source", command=self.remove_folder)
        filemenu.add_command(label="Choose destination...", command=self.choose_destination)
        filemenu.add_separator()
        filemenu.add_command(label="Export scan to CSV...", command=self.export_csv)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self._on_close)
        bar.add_cascade(label="File", menu=filemenu)
        actions = tk.Menu(bar, tearoff=False)
        actions.add_command(label="Scan folders", command=self.start_scan, accelerator="F5")
        actions.add_command(label="Organize with Local AI (Auto Copy)", command=self.auto_organize)
        actions.add_command(label="First-run AI setup...", command=self.setup_assistant)
        actions.add_command(label="Clear local analysis cache...", command=self.clear_analysis_cache)
        actions.add_command(label="Select all Ready files", command=self.select_ready)
        actions.add_command(label="Organize selected...", command=self.organize_selected)
        actions.add_command(label="Undo last batch...", command=self.undo, accelerator="Ctrl+Z")
        actions.add_command(label="Manage Subjects...", command=self.manage_subjects)
        bar.add_cascade(label="Actions", menu=actions)
        view = tk.Menu(bar, tearoff=False)
        view.add_command(label="Files", command=self.show_files)
        view.add_command(label="History", command=self.show_history)
        view.add_command(label="Show/hide advanced manual controls", command=self.toggle_advanced)
        view.add_separator()
        view.add_checkbutton(label="Include subfolders", variable=self.recursive_var, command=self._persist)
        view.add_checkbutton(label="Read document contents", variable=self.read_var, command=self._persist)
        bar.add_cascade(label="View", menu=view)
        helpmenu = tk.Menu(bar, tearoff=False)
        helpmenu.add_command(label="Create sample demo", command=self.make_demo)
        helpmenu.add_command(label="How sorting works", command=self.show_classification_help)
        helpmenu.add_command(label="License agreement", command=lambda: self.show_document("EULA.txt", "SORTIQ License Agreement"))
        helpmenu.add_command(label="Privacy policy", command=lambda: self.show_document("PRIVACY.txt", "SORTIQ Privacy Policy"))
        helpmenu.add_command(label="About SORTIQ", command=lambda: messagebox.showinfo(
            "About SORTIQ", "SORTIQ Classic — selected-folder organizer.\n\n"
            "Preview categories before copying or moving. No cloud uploads.\n"
            "For safety, Copy is the default. Undo reverses the last batch."))
        bar.add_cascade(label="Help", menu=helpmenu)
        self.configure(menu=bar)
        self.bind_all("<Control-o>", lambda e: self.add_folder())
        self.bind_all("<F5>", lambda e: self.start_scan())
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-f>", lambda e: self._focus_search())

    def _toolbar(self):
        """Original brightly colored icons in a classic WinRAR-style compact toolbar."""
        bar = tk.Frame(self, bg=BG, bd=0, pady=3, padx=6, highlightthickness=1,
                       highlightbackground="#DBDBDB")
        bar.pack(fill="x", side="top")

        def action(title, icon_name, handler, tooltip=""):
            btn = tk.Button(bar, text=title, command=handler,
                            image=self.icons.get(icon_name), compound="top", bg=BG, fg=TEXT,
                            activebackground="#DCEBFC", activeforeground=TEXT,
                            font=(FONT, 9), bd=0, relief="flat", padx=7, pady=2,
                            cursor="hand2", width=78, height=72)
            btn.pack(side="left", padx=1)
            return btn

        self.add_button = action("Add Folder", "add", self.add_folder)
        self.auto_button = action("AI Organize", "demo", self.auto_organize)
        self.undo_button = action("Undo", "undo", self.undo)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=7, pady=6)
        action("Files", "files", self.show_files)
        action("History", "history", self.show_history)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=7, pady=6)
        action("AI Setup", "why", self.setup_assistant)
        action("Advanced", "scan", self.toggle_advanced)

    def _address_bar(self):
        frame = ttk.Frame(self, padding=(12, 3, 12, 7))
        frame.pack(fill="x")
        ttk.Label(frame, text="Destination:").pack(side="left", padx=(0, 8))
        self.dst_entry = ttk.Entry(frame, textvariable=self.destination_var)
        self.dst_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(frame, text="Browse...", command=self.choose_destination).pack(side="left", padx=(7, 0))

    def _main_area(self):
        panel = ttk.Panedwindow(self, orient="horizontal")
        panel.pack(fill="both", expand=True, padx=9, pady=(2, 3))
        left = ttk.Frame(panel)
        right = ttk.Frame(panel)
        panel.add(left, weight=1)
        panel.add(right, weight=4)
        ttk.Label(left, text="Folders", font=(FONT, 9, "bold")).pack(anchor="w", padx=4, pady=(0, 6))
        nav_outer = ttk.Frame(left)
        nav_outer.pack(fill="both", expand=True)
        self.nav_tree = ttk.Treeview(nav_outer, show="tree", selectmode="browse")
        nav_scroll = ttk.Scrollbar(nav_outer, orient="vertical", command=self.nav_tree.yview)
        self.nav_tree.configure(yscrollcommand=nav_scroll.set)
        nav_scroll.pack(side="right", fill="y")
        self.nav_tree.pack(side="left", fill="both", expand=True)
        self.nav_tree.bind("<<TreeviewSelect>>", self._nav_selected)
        right_head = ttk.Frame(right)
        right_head.pack(fill="x", pady=(0, 6))
        ttk.Label(right_head, text="Files", font=(FONT, 9, "bold")).pack(side="left", padx=(5, 10))
        ttk.Label(right_head, text="Find:").pack(side="left")
        self.search_entry = ttk.Entry(right_head, textvariable=self.search_var, width=25)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))
        self.filter_box = ttk.Combobox(right_head, textvariable=self.filter_var, width=17, state="readonly",
                                       values=("All files", "Ready", "Needs Review", "College", "Astro Business", "Personal & Misc"))
        self.filter_box.pack(side="left", padx=(0, 4))
        self.switch_panel = ttk.Frame(right)
        self.switch_panel.pack(fill="both", expand=True)
        self.files_panel = ttk.Frame(self.switch_panel)
        self.history_panel = ttk.Frame(self.switch_panel)
        self._file_list()
        self._history_list()
        self.show_files()

    def _file_list(self):
        # Name lives in #0 so the app can show native colorful per-file icons.
        cols = ("size", "type", "category", "status", "location")
        self.tree = ttk.Treeview(self.files_panel, columns=cols, show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Name", command=lambda: self._sort_by("file"))
        self.tree.column("#0", width=240, minwidth=160, stretch=True, anchor="w")
        spec = (("size", "Size", 78, False),
                ("type", "Type", 70, False), ("category", "Suggested folder", 240, True),
                ("status", "Status", 108, False), ("location", "Original folder", 240, True))
        for col, title, width, stretch in spec:
            self.tree.heading(col, text=title, command=lambda key=col: self._sort_by(key))
            self.tree.column(col, width=width, minwidth=65, stretch=stretch, anchor="w")
        scroll_y = ttk.Scrollbar(self.files_panel, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self.files_panel, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("review", foreground="#9A5300")
        self.tree.tag_configure("ready", foreground=TEXT)
        self.tree.bind("<<TreeviewSelect>>", self._select_change)
        self.tree.bind("<Double-1>", lambda event: self.open_selected_file())

    def _history_list(self):
        cols = ("date", "action", "file", "destination", "status")
        self.history_tree = ttk.Treeview(self.history_panel, columns=cols, show="headings")
        for col, title, width in (("date", "Date", 155), ("action", "Action", 80),
                                  ("file", "File name", 245), ("destination", "Destination", 430), ("status", "Result", 105)):
            self.history_tree.heading(col, text=title)
            self.history_tree.column(col, width=width, minwidth=70)
        s = ttk.Scrollbar(self.history_panel, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=s.set)
        s.pack(side="right", fill="y")
        self.history_tree.pack(side="left", fill="both", expand=True)

    def _bottom_bar(self):
        lower = ttk.Frame(self, padding=(10, 5, 10, 6))
        lower.pack(fill="x", side="bottom")
        self.selection_frame = lower
        detail = ttk.Frame(lower)
        detail.pack(fill="x", pady=(0, 6))
        ttk.Label(detail, text="Suggestion:").pack(side="left")
        ttk.Label(detail, textvariable=self.detail_var, foreground=GRAY).pack(side="left", padx=(6, 0))
        controls = ttk.Frame(lower)
        controls.pack(fill="x")
        ttk.Label(controls, text="Set category:").pack(side="left", padx=(0, 7))
        self.category_dropdown = ttk.Combobox(controls, textvariable=self.category_var, values=CATEGORY_TREE,
                                               state="readonly", width=37)
        self.category_dropdown.pack(side="left")
        ttk.Button(controls, text="Apply", command=self.apply_category).pack(side="left", padx=5)
        ttk.Button(controls, text="Open File", command=self.open_selected_file).pack(side="left", padx=4)
        ttk.Button(controls, text="Why this category?", command=self.explain_selected).pack(side="left", padx=3)
        ttk.Separator(controls, orient="vertical").pack(side="left", fill="y", padx=8, pady=3)
        ttk.Radiobutton(controls, text="Copy (safe)", variable=self.mode_var, value="copy",
                        command=self._persist).pack(side="left", padx=3)
        ttk.Radiobutton(controls, text="Move", variable=self.mode_var, value="move",
                        command=self._persist).pack(side="left", padx=3)
        ttk.Button(controls, text="Select Ready", command=self.select_ready).pack(side="right", padx=2)

    def toggle_advanced(self):
        if not self.history_visible:
            self.advanced_var.set(not self.advanced_var.get())
        if self.advanced_var.get() and not self.history_visible:
            self.selection_frame.pack(fill="x", side="bottom")
        else:
            self.selection_frame.pack_forget()
        self.message_var.set("Advanced file controls " + ("visible" if self.advanced_var.get() else "hidden") + ".")

    def _focus_search(self):
        self.show_files()
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def show_files(self):
        was_history = self.history_visible
        self.history_panel.pack_forget()
        self.files_panel.pack(fill="both", expand=True)
        self.history_visible = False
        if hasattr(self, "selection_frame"):
            if self.advanced_var.get():
                self.selection_frame.pack(fill="x", side="bottom")
            else:
                self.selection_frame.pack_forget()
        self.refresh_table()
        if was_history:
            self.message_var.set("File list. Select Ready files to organize, or open a file to inspect it.")

    def show_history(self):
        self.files_panel.pack_forget()
        self.history_panel.pack(fill="both", expand=True)
        self.history_visible = True
        if hasattr(self, "selection_frame"):
            self.selection_frame.pack_forget()
        self.refresh_history()
        self.message_var.set("History shows recorded actions. Undo reverses the last batch only.")

    def _refresh_folders(self):
        self.nav_tree.delete(*self.nav_tree.get_children())
        self.nav_paths.clear()
        self.nav_tree.insert("", "end", iid="all", text="All selected folders", open=True,
                             image=self.icons.get("folder_small"))
        self.nav_paths["all"] = None
        folder_count = 0
        for i, root_text in enumerate(self.folders):
            root = Path(root_text)
            root_id = f"src:{i}"
            root_icon = ("folder-blue" if "college" in root.name.lower() else
                         "folder-purple" if "astro" in root.name.lower() else "folder")
            self.nav_tree.insert("all", "end", iid=root_id, text=root.name or str(root), open=True,
                                 image=self.icons.get(root_icon + "_small"))
            self.nav_paths[root_id] = root
            seen: dict[Path, str] = {root: root_id}
            for row in self.rows:
                try:
                    rel = row.source.parent.relative_to(root)
                except ValueError:
                    continue
                cursor = root
                parent = root_id
                for name in rel.parts:
                    cursor = cursor / name
                    if cursor not in seen:
                        if folder_count >= 1800:
                            break
                        iid = f"folder:{i}:{folder_count}"
                        folder_count += 1
                        self.nav_tree.insert(parent, "end", iid=iid, text=name, open=False,
                                             image=self.icons.get("folder_small"))
                        seen[cursor] = iid
                        self.nav_paths[iid] = cursor
                    parent = seen.get(cursor, parent)
        # Do not destroy the current file-list folder filter unless that folder vanished.
        matches = [iid for iid, path in self.nav_paths.items() if path == self.active_folder]
        self.nav_tree.selection_set(matches[0] if matches else "all")

    def _nav_selected(self, event=None):
        selection = self.nav_tree.selection()
        self.active_folder = self.nav_paths.get(selection[0]) if selection else None
        self.refresh_table()

    def add_folder(self):
        path = filedialog.askdirectory(title="Choose a source folder")
        if path:
            resolved = str(Path(path).resolve())
            if resolved not in self.folders:
                self.folders.append(resolved)
                self._refresh_folders()
                self._persist()
                self.message_var.set(f"Added {resolved}. Press Scan to inspect files.")

    def remove_folder(self):
        selected = self.nav_tree.selection()
        iid = selected[0] if selected else ""
        if not iid or iid == "all":
            messagebox.showinfo("Select source folder", "Select a source folder on the left first.\nRemoving a source never deletes its files.")
            return
        # Removing a child of a source removes the selected source from watch list, not files.
        while iid and not iid.startswith("src:"):
            iid = self.nav_tree.parent(iid)
        if not iid:
            return
        idx = int(iid.split(":", 1)[1])
        if idx < len(self.folders):
            removed = self.folders.pop(idx)
            self.active_folder = None
            self._refresh_folders()
            self._persist()
            self.message_var.set(f"Removed source from list: {removed}. No files were deleted.")

    def choose_destination(self):
        path = filedialog.askdirectory(title="Choose destination library")
        if path:
            self.destination_var.set(str(Path(path).resolve()))
            self._persist()

    def _persist(self):
        save({"folders": self.folders, "destination": self.destination_var.get(),
              "recursive": self.recursive_var.get(), "read_contents": self.read_var.get(),
              "mode": self.mode_var.get()})

    def manage_subjects(self):
        if self.busy:
            messagebox.showinfo("SORTIQ", "Finish scanning before editing subjects.")
            return
        SubjectManager(self, self.vocab, self.vocab_path,
                       lambda: self.category_dropdown.configure(values=CATEGORY_TREE))

    def clear_analysis_cache(self):
        if self.busy:
            messagebox.showinfo("SORTIQ", "Finish the current operation first.")
            return
        if not messagebox.askyesno("Clear analysis cache", "Remove locally cached document text?\n\nThis does not delete original files, model weights, or operation history. Subsequent scans will re-extract documents."):
            return
        from .engine import app_data_dir
        target = app_data_dir() / "analysis-cache.sqlite3"
        try:
            target.unlink(missing_ok=True)
            self.message_var.set("Document text cache cleared.")
        except OSError as exc:
            messagebox.showerror("Cache deletion failed", str(exc))

    def setup_assistant(self):
        # The startup timer, toolbar, or AI Organize can all request setup.
        # Reuse the existing modal instead of opening a second copy.
        if self._setup_window is not None:
            try:
                if self._setup_window.winfo_exists():
                    self._setup_window.lift()
                    self._setup_window.focus_force()
                    return
            except tk.TclError:
                pass
            self._setup_window = None
        if self.busy:
            messagebox.showinfo("SORTIQ", "Finish the current file operation first.")
            return
        self._setup_window = Onboarding(self, self._onboarding_complete,
                                        current_description=self.profile.get("description", "") if self.profile else "")

    def _onboarding_complete(self, profile: dict, folders: list[str], auto_start: bool, destination: str):
        self.profile = profile
        register_profile(profile)
        self.folders = folders
        self.destination_var.set(destination)
        self.category_dropdown.configure(values=CATEGORY_TREE)
        self._refresh_folders()
        # The automatic pipeline always copies. Manual mode remains separate.
        self.mode_var.set("copy")
        self._persist()
        self.message_var.set(f"AI profile saved. {len(profile['categories'])} subject folders defined.")
        if auto_start:
            self.after(150, self.auto_organize)

    def auto_organize(self):
        """No per-file selection required. Scanner + classifier + safe copy happen in one worker."""
        if self.busy: return
        if self.profile is None:
            self.setup_assistant()
            return
        if not self.folders:
            messagebox.showinfo("Choose folders", "Add a source folder in AI Setup first.")
            return
        root_text = self.destination_var.get().strip()
        if not root_text:
            messagebox.showerror("Choose destination", "Choose an organized library folder.")
            return
        root = Path(root_text).expanduser().resolve()
        self.mode_var.set("copy")
        self._persist()
        self._busy(True, "Preparing local AI (no document uploads)...")
        self.cancel_event.clear()
        profile = dict(self.profile)
        roots = tuple(self.folders)

        def job():
            try:
                model = LocalSemanticModel(consent_to_download=bool(profile.get("ai_enabled")))
                self.jobs.put(("progress", "Loading local AI model; initial download can take time..."))
                model_ok = model.start()
                if profile.get("ai_enabled") and not model_ok:
                    self.jobs.put(("error", "Local AI was requested but could not load. No files were copied. "
                                          + model.error[:400] + ". Check the internet/model installation and retry."))
                    return
                ai_note = "Local AI semantic embeddings" if model.engine else "Keywords only — local AI unavailable"
                self.jobs.put(("progress", f"{ai_note}. Inspecting documents..."))
                classifier = HybridClassifier(profile, model)
                rows = auto_scan(roots, root, classifier, cancel=self.cancel_event,
                                 progress=lambda n, file: self.jobs.put(("progress", f"Analyzed {n:,}: {file}")))
                ready = [r for r in rows if r.status == "Ready" and r.category != "Needs Review"]
                if self.cancel_event.is_set():
                    self.jobs.put(("error", "Automatic operation stopped before copying."))
                    return
                self.jobs.put(("progress", f"Copying {len(ready):,} classified files..."))
                result = sort_files(ready, root, roots, self.history, mode="copy",
                                    progress=lambda n, total, filename:
                                    self.jobs.put(("progress", f"Copied/checking {n}/{total}: {filename}"))) if ready else None
                if result is None:
                    from .engine import SortResult
                    result = SortResult("",0,0,0,())
                self.jobs.put(("auto_done", (rows,result,ai_note)))
            except Exception as exc:
                self.jobs.put(("error", f"AI automatic organization failed: {exc}"))
        threading.Thread(target=job, daemon=True).start()

    def start_scan(self):
        if self.busy:
            return
        if not self.folders:
            messagebox.showinfo("No sources", "Click Add Folder and choose the folder(s) you want SORTIQ to scan.")
            return
        dest_text = self.destination_var.get().strip()
        if not dest_text:
            messagebox.showerror("Destination missing", "Choose a destination library folder.")
            return
        destination = Path(dest_text).expanduser()
        self._persist()
        self._busy(True, "Scanning selected folders. No files will move.")
        self.cancel_event.clear()
        roots = tuple(self.folders)
        read_contents = self.read_var.get()
        recursive = self.recursive_var.get()

        def job():
            try:
                result = scan(roots, destination, read_contents=read_contents, recursive=recursive,
                              progress=lambda n, filename: self.jobs.put(("progress", f"Scanned {n:,}: {filename}")),
                              cancel=self.cancel_event, vocabulary=self.vocab)
                self.jobs.put(("scan_done", result))
            except Exception as error:
                self.jobs.put(("error", f"Scan failed: {error}"))
        threading.Thread(target=job, daemon=True).start()

    def _poll_jobs(self):
        try:
            while True:
                kind, payload = self.jobs.get_nowait()
                if kind == "progress":
                    self.message_var.set(payload)
                elif kind == "scan_done":
                    self.rows = payload
                    self._busy(False, f"Scan complete: {len(self.rows):,} files. Select Ready files to organize.")
                    self._refresh_folders()
                    self.show_files()
                elif kind == "auto_done":
                    rows, result, ai_note = payload
                    self.rows = rows
                    self._busy(False, f"Auto organize complete. {result.sorted} copied; {sum(r.status == 'Review' for r in rows)} left untouched. {ai_note}")
                    self._refresh_folders()
                    self.show_files()
                    self.refresh_history()
                    messagebox.showinfo("SORTIQ automatic organization",
                                        f"Files scanned: {len(rows):,}\nAutomatically copied: {result.sorted:,}\n"
                                        f"Exact duplicates skipped: {result.duplicates:,}\n"
                                        f"Uncertain files untouched: {sum(r.status == 'Review' for r in rows):,}\n"
                                        f"Errors: {len(result.failures)}\n\nMode: {ai_note}\n"
                                        "Originals were kept. You can inspect reasons or undo the copied batch.")
                elif kind == "sort_done":
                    result = payload
                    self._busy(False, f"Organized {result.sorted} files; skipped {result.duplicates} duplicates.")
                    self.refresh_history()
                    messagebox.showinfo("Organize finished", f"Organized: {result.sorted}\n"
                                        f"Exact duplicates skipped: {result.duplicates}\n"
                                        f"Review skipped: {result.skipped}\nErrors: {len(result.failures)}" +
                                        ("\n\n" + "\n".join(result.failures[:5]) if result.failures else ""))
                    self.start_scan()
                elif kind == "undo_done":
                    restored, issues = payload
                    self._busy(False, f"Undo reversed {restored} operations.")
                    self.refresh_history()
                    messagebox.showinfo("Undo result", f"Reversed: {restored}\nIssues: {len(issues)}" +
                                        ("\n\n" + "\n".join(issues[:5]) if issues else ""))
                    if self.folders:
                        self.start_scan()
                elif kind == "error":
                    self._busy(False, "Operation failed. See error details.")
                    messagebox.showerror("SORTIQ", payload)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(120, self._poll_jobs)
        # First-run setup is scheduled only once in __init__.
        # Scheduling it here opened an unbounded number of dialogs.

    def _busy(self, value: bool, message: str):
        self.busy = value
        self.message_var.set(message)
        state = "disabled" if value else "normal"
        # The classic UI no longer has the legacy scan_button / sort_button.
        # Disable only controls that exist in this simplified toolbar.
        for button_name in ("auto_button", "undo_button"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.configure(state=state)

    def _sort_by(self, key: str):
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = False
        self.refresh_table()

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return
        selection = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        search = self.search_var.get().casefold().strip()
        flt = self.filter_var.get()
        filtered: list[tuple[int, Suggestion]] = []
        for index, row in enumerate(self.rows):
            if self.active_folder is not None and not inside(row.source, self.active_folder):
                continue
            if search and search not in f"{row.source.name} {row.source.parent} {row.category} {row.reason}".casefold():
                continue
            if flt == "Ready" and row.status != "Ready":
                continue
            if flt == "Needs Review" and row.status == "Ready":
                continue
            if flt in ("College", "Astro Business", "Personal & Misc") and not row.category.startswith(flt):
                continue
            filtered.append((index, row))

        def sortval(pair):
            row = pair[1]
            return {"file": row.source.name.casefold(), "size": row.size, "type": row.source.suffix.casefold(),
                    "category": row.category.casefold(), "status": row.status, "location": str(row.source.parent).casefold()}[self.sort_key]
        filtered.sort(key=sortval, reverse=self.sort_reverse)
        for idx, row in filtered:
            self.tree.insert("", "end", iid=str(idx), text=row.source.name,
                             image=self._file_icon(row.source), values=(
                fmt_size(row.size), row.source.suffix[1:].upper() or "FILE",
                row.category.replace(" / ", "  >  "),
                "Ready" if row.status == "Ready" else "Needs Review",
                str(row.source.parent)), tags=("ready" if row.status == "Ready" else "review",))
        reselection = [iid for iid in selection if self.tree.exists(iid)]
        if reselection:
            self.tree.selection_set(reselection)
        ready = sum(row.status == "Ready" for _, row in filtered)
        self.count_var.set(f"{len(filtered):,} files  |  {ready:,} ready  |  {len(filtered)-ready:,} review")

    def _select_change(self, event=None):
        selection = self.tree.selection()
        if not selection:
            self.detail_var.set("Select a file to see its suggested category and reason.")
            return
        row = self.rows[int(selection[0])]
        self.category_var.set(row.category)
        description = row.reason.replace("\n", " ")
        self.detail_var.set(f"{row.category}  —  {description[:95]}" if len(selection) == 1 else f"{len(selection)} files selected")

    def show_document(self, filename: str, title: str):
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        path = base / "docs" / filename
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            messagebox.showerror(title, "Documentation file is missing from this installation.")
            return
        self._text_dialog(title, body)

    def show_classification_help(self):
        info = (
            "SORTIQ 2.0 Auto mode can use local ONNX semantic embeddings when downloaded with consent.\n"
            "Without a local model, it labels its result as keywords-only.\n\n"
            "V1.3 manual mode uses offline RULES, not an AI model.\n\n"
            "BROAD CATEGORY (College versus Astro Business)\n"
            "Filename keyword: +6 per matching cue\n"
            "Parent folder path: +2 per cue (up to 3)\n"
            "Document text: +1 per cue (up to 4)\n\n"
            "SPECIFIC SUBCATEGORY\n"
            "Filename keyword: +7 per cue\n"
            "Folder path: +1 per cue (up to 3)\n"
            "Document text: +1 per cue (up to 2)\n\n"
            "Planetary placement and Personal/Misc have special rules.\n"
            "Confidence is heuristic, NOT an AI probability.\n\n"
            "Supported content: TXT, MD, CSV, PDF with extractable text, DOCX, PPTX, XLSX.\n"
            "Scanned PDFs, JPGs, old DOC/PPT, ZIPs are NOT semantically read.\n"
            "Ambiguous documents go to Needs Review.\n\n"
            "Select any file and click 'Why this category?' for matched clues.\n"
            "Scanning never moves your documents. Copy mode is the default."
        )
        self._text_dialog("How SORTIQ classifies files", info)

    def _text_dialog(self, title: str, body: str):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("710x580")
        dlg.minsize(500,380)
        dlg.transient(self)
        if "app" in self.icons:
            dlg.iconphoto(False, self.icons["app"])
        tk.Label(dlg, text=title, font=(FONT,12,"bold"), padx=15, pady=12, anchor="w").pack(fill="x")
        content = scrolledtext.ScrolledText(dlg, wrap="word", font=(FONT,10), bg=WHITE,
                                            padx=14, pady=12, relief="flat")
        content.pack(fill="both", expand=True, padx=12,pady=(0,8))
        content.insert("1.0", body)
        content.configure(state="disabled")
        ttk.Button(dlg, text="Close", command=dlg.destroy).pack(side="right", padx=16,pady=(0,12))

    def explain_selected(self):
        if self.history_visible:
            self.show_files()
        ids = self.tree.selection()
        if not ids:
            messagebox.showinfo("Choose a file", "Select a scanned file to see the classification evidence.")
            return
        row = self.rows[int(ids[0])]
        details = (f"FILE: {row.source.name}\n"
                   f"ORIGINAL LOCATION: {row.source.parent}\n"
                   f"STATUS: {row.status}\n"
                   f"CURRENT DESTINATION: {row.category}\n\n")
        if row.manually_set:
            details += "You manually overrode the category. Original scan evidence follows.\n\n"
        details += row.explanation or row.reason
        if row.error:
            details += f"\n\nPARSER NOTE: {row.error}"
        self._text_dialog("Why this category?", details)

    def apply_category(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select files", "Select one or more files first.")
            return
        category = self.category_var.get()
        for iid in selected:
            self.rows[int(iid)] = override(self.rows[int(iid)], category)
        self.refresh_table()
        self.tree.selection_set([iid for iid in selected if self.tree.exists(iid)])
        self.message_var.set(f"Applied category to {len(selected)} files. No files have moved yet.")

    def select_ready(self):
        self.show_files()
        eligible = [iid for iid in self.tree.get_children() if self.rows[int(iid)].status == "Ready"]
        if eligible:
            self.tree.selection_set(eligible)
            self.tree.see(eligible[0])
        else:
            self.tree.selection_remove(self.tree.selection())
        self.message_var.set(f"Selected {len(eligible):,} ready files. Copy is safer than Move.")

    def open_selected_file(self):
        chosen = self.tree.selection()
        if not chosen:
            return
        path = self.rows[int(chosen[0])].source
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open file", str(exc))

    def organize_selected(self):
        if self.busy:
            return
        ids = self.tree.selection()
        if not ids:
            messagebox.showinfo("Select files", "Select files in the list, or click Select Ready.")
            return
        selected = [self.rows[int(iid)] for iid in ids]
        ready = [row for row in selected if row.status == "Ready" and row.category != "Needs Review"]
        if not ready:
            messagebox.showinfo("Review needed", "Choose a specific category for these files first.")
            return
        mode = self.mode_var.get()
        raw_root = self.destination_var.get().strip()
        if not raw_root:
            messagebox.showerror("Destination missing", "Choose destination library first.")
            return
        root = Path(raw_root).expanduser().resolve()
        action = "COPY" if mode == "copy" else "MOVE"
        details = "Original files will remain where they are." if mode == "copy" else (
            "Original files will move after verifying copies. Undo can restore unchanged files.")
        if not messagebox.askyesno("Confirm organization", f"{action} {len(ready)} files into:\n{root}\n\n"
                                   f"{details}\n\nExisting files will not be overwritten. Continue?",
                                   icon="warning" if mode == "move" else "question"):
            return
        self._persist()
        self._busy(True, f"{action.title()}ing {len(ready)} files...")
        sources = tuple(self.folders)

        def job():
            try:
                result = sort_files(ready, root, sources, self.history, mode=mode,
                                    progress=lambda i, total, name: self.jobs.put(("progress", f"{i}/{total}: {name}")))
                self.jobs.put(("sort_done", result))
            except Exception as exc:
                self.jobs.put(("error", f"Organize failed: {exc}"))
        threading.Thread(target=job, daemon=True).start()

    def undo(self):
        if self.busy:
            return
        if not self.history.last_batch():
            messagebox.showinfo("Nothing to undo", "No completed batch can be undone.")
            return
        if not messagebox.askyesno("Undo last batch", "Undo the most recent organized batch?\n\n"
                                   "Edited or occupied files will be skipped, never overwritten."):
            return
        self._busy(True, "Undoing last batch...")

        def job():
            try:
                result = undo_last(self.history,
                                   progress=lambda i, total, name: self.jobs.put(("progress", f"Undo {i}/{total}: {name}")))
                self.jobs.put(("undo_done", result))
            except Exception as exc:
                self.jobs.put(("error", f"Undo failed: {exc}"))
        threading.Thread(target=job, daemon=True).start()

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        self.history_tree.delete(*self.history_tree.get_children())
        for stamp, original, dest, mode, status, _note in self.history.recent():
            self.history_tree.insert("", "end", values=(datetime.fromtimestamp(stamp).strftime("%d %b %Y %H:%M"),
                                                     mode.upper(), Path(original).name, str(dest), status.upper()))

    def export_csv(self):
        if not self.rows:
            messagebox.showinfo("No results", "Scan some folders first.")
            return
        filename = filedialog.asksaveasfilename(title="Export suggestions", defaultextension=".csv",
                                                filetypes=[("CSV file", "*.csv")], initialfile="SORTIQ_preview.csv")
        if filename:
            with open(filename, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["File", "Original folder", "Suggested folder", "Match", "Status", "Size", "Reason"])
                for row in self.rows:
                    writer.writerow([row.source.name, str(row.source.parent), row.category,
                                     row.display_confidence, row.status, row.size, row.reason])
            self.message_var.set(f"Exported {len(self.rows):,} suggestions to CSV.")

    def make_demo(self):
        from .demo import create_demo
        try:
            folder = create_demo()
            if str(folder) not in self.folders:
                self.folders.append(str(folder))
                self._refresh_folders()
            self._persist()
            messagebox.showinfo("Sample folder created", f"Sample documents created here:\n{folder}\n\nClick Scan (F5).")
        except Exception as error:
            messagebox.showerror("Sample folder", str(error))

    def _on_close(self):
        self.cancel_event.set()
        self._persist()
        self.destroy()


def main():
    SortiqApp().mainloop()
