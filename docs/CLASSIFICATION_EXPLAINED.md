> **Legacy V1.3 manual classification reference.** SORTIQ 2.0 automatic mode is documented in `../README.md` and `RELEASE_READINESS.md`.

# How SORTIQ classifies files (V1.2)

SORTIQ currently uses **local, hand-authored keyword rules**, not an AI model. Filenames matter most, but folder paths and supported document contents also matter. No internet access or cloud API is used.

## Level 1: choose a broad domain

For each of **College** and **Astro Business**, SORTIQ scans the normalized filename, parent path, and up to 40,000 characters of extractable text (the parser limit; the classification function itself can accept more). Each matching domain keyword contributes:

- Filename: **6 points per distinct matched cue**.
- Folder path: **2 points per distinct cue, maximum 3 matches**.
- Document text: **1 point per distinct cue, maximum 4 matches**.

Domain-specific special rules can add weight for a generic assignment/case-study filename or planet+house filename. If both domains are close or there is no strong match, the engine tries simple personal/miscellaneous filename-only keywords, then marks the file **Needs Review**.

## Level 2: select the subcategory

Within the winning domain, individual category cues are weighted differently:

- Filename: **7 points per distinct cue**.
- Folder path: **1 point per cue, maximum 3**.
- Document text: **1 point per cue, maximum 2**.

Planet+house combinations can use special placement rules. Personal/Misc currently relies on filenames only.

## Example

`Document123.pdf` in `Downloads` with contents that mention `Federal Bank`, `PGDM`, and `campus placement` can be classified as College / Placements & Interviews from the document text. The confidence depends on the combined evidence and special rules. Because filename signals are dominant, content-only classification may be less certain; inspect the per-file **Why?** dialog and correct any inaccurate category.

## Limits

- Text extraction supports TXT, MD, CSV, PDFs containing selectable text, DOCX, PPTX, and XLSX. It does **not** perform OCR.
- Old .doc/.ppt, locked or image-only PDFs, most pictures/audio/video, archives and unsupported formats are **not** semantically examined.
- The confidence percentage is a heuristic, **not** a statistical probability.
- Uncertain files should be reviewed; use **Copy (safe)** and start with a small test folder.
- Names and paths can contain sensitive information; SORTIQ processes them locally.
