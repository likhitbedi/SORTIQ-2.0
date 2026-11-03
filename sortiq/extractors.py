"""Bounded local text extraction. Readers are optional; no documents leave the PC."""
from __future__ import annotations

import csv
from pathlib import Path

TEXT_EXTS = {".txt", ".md", ".rst", ".json", ".xml", ".html", ".css", ".js", ".py", ".log", ".yaml", ".yml", ".sql"}
CONTENT_EXTS = TEXT_EXTS | {".csv", ".pdf", ".docx", ".pptx", ".xlsx"}
MAX_CHARS = 40_000


def get_text(path: Path) -> tuple[str, str | None]:
    """Returns a bounded excerpt and an optional explanation of parser problems."""
    suffix = path.suffix.lower()
    try:
        if suffix in TEXT_EXTS or suffix == ".csv":
            with path.open("r", encoding="utf-8", errors="replace") as f:
                return f.read(MAX_CHARS), None
        if suffix == ".docx":
            try:
                from docx import Document
            except ImportError:
                return "", "Install python-docx for Word content analysis"
            doc = Document(str(path))
            parts = []
            n = 0
            for paragraph in doc.paragraphs:
                parts.append(paragraph.text)
                n += len(paragraph.text)
                if n > MAX_CHARS:
                    break
            if n < MAX_CHARS:
                for table in doc.tables[:15]:
                    for row in table.rows[:60]:
                        line = " | ".join(cell.text for cell in row.cells)
                        parts.append(line)
                        n += len(line)
                        if n > MAX_CHARS: break
                    if n > MAX_CHARS: break
            return "\n".join(parts)[:MAX_CHARS], None
        if suffix == ".pptx":
            try:
                from pptx import Presentation
            except ImportError:
                return "", "Install python-pptx for slide content analysis"
            ppt = Presentation(str(path))
            snippets = []
            for slide in list(ppt.slides)[:70]:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        snippets.append(shape.text)
                    if shape.has_table:
                        for row in shape.table.rows[:40]:
                            snippets.append(" | ".join(cell.text for cell in row.cells))
                    if sum(len(x) for x in snippets) > MAX_CHARS:
                        break
                if sum(len(x) for x in snippets) > MAX_CHARS:
                    break
            return "\n".join(snippets)[:MAX_CHARS], None
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError:
                return "", "Install pypdf for PDF content analysis"
            reader = PdfReader(str(path), strict=False)
            snippets = []
            total_pages = len(reader.pages)
            page_ids = sorted(set(list(range(min(4,total_pages))) +
                                  [int(total_pages*f) for f in (.25,.5,.75)] +
                                  list(range(max(0,total_pages-2),total_pages))))[:11]
            for page_id in page_ids:
                page = reader.pages[page_id]
                snippets.append(page.extract_text() or "")
                if sum(len(x) for x in snippets) > MAX_CHARS:
                    break
            return "\n".join(snippets)[:MAX_CHARS], None
        if suffix == ".xlsx":
            try:
                from openpyxl import load_workbook
            except ImportError:
                return "", "Install openpyxl for spreadsheet content analysis"
            wb = load_workbook(str(path), read_only=True, data_only=True)
            text_parts = []
            try:
                for sh in wb.worksheets[:7]:
                    text_parts.append(sh.title)
                    for row in sh.iter_rows(min_row=1, max_row=80, max_col=14, values_only=True):
                        text_parts.append(" ".join(str(v) for v in row if v is not None))
                        if sum(map(len, text_parts)) > MAX_CHARS:
                            break
                    if sum(map(len, text_parts)) > MAX_CHARS:
                        break
            finally:
                wb.close()
            return "\n".join(text_parts)[:MAX_CHARS], None
    except Exception as exc:
        return "", f"Could not read document text ({type(exc).__name__})"
    return "", None
