"""Small self-contained demo library. Never writes over an existing file."""
from pathlib import Path
from .engine import default_library

DEMO_FILES = {
    "Random Downloads/Federal_Bank_Interview_Questions.txt": "PGDM placement preparation for Federal Bank. CASA, RBI, banking, wealth management.\n",
    "Random Downloads/Rural_Marketing_Project_Shakti.txt": "PIBM Rural Marketing course assignment on Project Shakti.\n",
    "Random Downloads/GoPro_Case_Study.txt": "College case study: GoPro brand extensions.\n",
    "Random Downloads/Prime_Marketing_Attendance.csv": "Student,Present\nStudent A,Yes\nStudent B,No\n",
    "Old Desk/Rahu_in_6th_House_Research.md": "# Astrology: Rahu in 6th House\nPlanetary placement reference for grahaswithlikhit.in.\n",
    "Old Desk/BPHS_Gulika_Calculation.txt": "Brihat Parashara Hora Shastra. Gulika Mandi calculation in Jyotish.\n",
    "Old Desk/GrahasWithLikhit_SEO_Keywords.txt": "Website ranking SEO indexing and keyword ideas for planetary placement pages.\n",
    "Old Desk/Astro_CRM_Lead_Inbox.txt": "Astrology business CRM lead inbox and client consultations.\n",
    "Other/Electricity_Bill_September.txt": "Household utility electricity bill.\n",
    "Other/Unknown_Document_8371.txt": "Unlabeled notes, no meaningful context for automatic filing.\n",
}


def create_demo(root: Path | None = None) -> Path:
    library = Path(root) if root is not None else default_library().parent / "SORTIQ Demo Input"
    for filename, content in DEMO_FILES.items():
        file = library / filename
        file.parent.mkdir(parents=True, exist_ok=True)
        if not file.exists():
            file.write_text(content, encoding="utf-8")
    _create_office_examples(library)
    return library.resolve()


def _write_simple_pdf(path: Path, text: str) -> None:
    """Create a valid, tiny text PDF using only the Python standard library."""
    ascii_text = text.encode("ascii", "replace").decode("ascii")
    ascii_text = ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 15 Tf 64 750 Td ({ascii_text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)


def _create_office_examples(library: Path) -> None:
    """Real DOCX/PPTX/XLSX/PDF examples; skip only if optional readers are missing."""
    docx_path = library / "Random Downloads" / "Banking_Interview_Preparation.docx"
    if not docx_path.exists():
        try:
            from docx import Document
            doc = Document()
            doc.add_heading("Federal Bank Campus Placement Preparation", 0)
            doc.add_paragraph("PIBM PGDM: sales and client acquisition interview notes, RBI and CASA.")
            doc.save(str(docx_path))
        except ImportError:
            pass

    pptx_path = library / "Old Desk" / "GrahasWithLikhit_SEO_Plan.pptx"
    if not pptx_path.exists():
        try:
            from pptx import Presentation
            ppt = Presentation()
            slide = ppt.slides.add_slide(ppt.slide_layouts[1])
            slide.shapes.title.text = "Astrology business: website SEO plan"
            slide.placeholders[1].text = "Google Search Console, indexing, keywords, planetary placements"
            ppt.save(str(pptx_path))
        except ImportError:
            pass

    xlsx_path = library / "Random Downloads" / "Semester_Notes.xlsx"
    if not xlsx_path.exists():
        try:
            from openpyxl import Workbook
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "PGDM Brand Management"
            sheet.append(["PIBM PGDM", "Brand Management", "Kapferer", "Course notes"])
            workbook.save(str(xlsx_path))
        except ImportError:
            pass

    pdf_path = library / "Old Desk" / "BPHS_Reference_Summary.pdf"
    if not pdf_path.exists():
        _write_simple_pdf(pdf_path, "BPHS Parashara Jyotish research: Gulika, Shadbala and Mahadasha")
