"""Transparent, editable taxonomy and keyword-based classification."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")

CATEGORY_TREE = [
    "College / Placements & Interviews",
    "College / Case Studies",
    "College / Assignments",
    "College / Presentations",
    "College / Subjects / Rural Marketing",
    "College / Subjects / Services Marketing",
    "College / Subjects / Brand Management",
    "College / Subjects / Project Management",
    "College / Subjects / Banking & Sales",
    "College / Notes & Exams",
    "College / Attendance & Admin",
    "College / Other College",
    "Astro Business / BPHS & Jyotish Research",
    *[f"Astro Business / Planetary Placements / {p}" for p in PLANETS],
    "Astro Business / Website & SEO",
    "Astro Business / CRM & Technology",
    "Astro Business / Consultations & Clients",
    "Astro Business / Content & Marketing",
    "Astro Business / Finance & Operations",
    "Astro Business / Other Astro",
    "Personal & Misc / Photos & Videos",
    "Personal & Misc / Bills & Receipts",
    "Personal & Misc / IDs & Forms",
    "Personal & Misc / Travel",
    "Personal & Misc / Other",
    "Needs Review",
]

COLLEGE_CUES = (
    "college", "pgdm", "pibm", "semester", "faculty", "attendance", "placement", "federal bank",
    "case study", "assignment", "marketing management", "services marketing", "rural marketing",
    "brand management", "project management", "sales and client acquisition", "sip", "wip",
    "kotler", "kapferer", "class notes", "exam preparation", "interview questions", "academic",
)
ASTRO_CUES = (
    "astro", "astrology", "jyotish", "kundali", "horoscope", "nakshatra", "grahaswithlikhit",
    "grahas with likhit", "bphs", "brihat parashara", "mahadasha", "antardasha", "shadbala",
    "lagna", "graha", "upagraha", "birth chart", "planetary placement", "vimshottari",
    "rahu", "ketu", "mangal", "shukra", "shani", "surya", "chandra", "guru",
)

COLLEGE_RULES = [
    ("College / Placements & Interviews", ("federal bank", "campus placement", "interview", "resume", "cv", "recruitment", "job description", "jd")),
    ("College / Attendance & Admin", ("attendance", "prime marketing", "faculty", "class roster", "timetable", "time table")),
    ("College / Case Studies", ("case study", "case analysis", "case exhibit", "go pro", "gopro", "netflix case", "amazon logistics")),
    ("College / Assignments", ("assignment", "submission", "coursework", "graded report")),
    ("College / Subjects / Rural Marketing", ("rural marketing", "project shakti", "rural market")),
    ("College / Subjects / Services Marketing", ("services marketing", "service marketing", "service blueprint")),
    ("College / Subjects / Brand Management", ("brand management", "brand equity", "kapferer", "brand identity")),
    ("College / Subjects / Project Management", ("project management", "pmbok", "critical path", "project charter")),
    ("College / Subjects / Banking & Sales", ("casa", "rbi", "banking", "wealth management", "client acquisition", "sales management")),
    ("College / Notes & Exams", ("exam", "revision", "study notes", "lecture notes", "syllabus", "question bank", "flashcards")),
    ("College / Presentations", ("presentation", "slide deck", "ppt", "seminar")),
]
ASTRO_RULES = [
    ("Astro Business / BPHS & Jyotish Research", ("bphs", "parashara", "shadbala", "gulika", "mandi", "jyotish", "upagraha", "naisargika", "dasha research")),
    ("Astro Business / Website & SEO", ("seo", "search console", "gsc", "keyword", "indexing", "wordpress", "sitemap", "ranking", "website", "search performance", "analytics")),
    ("Astro Business / CRM & Technology", ("crm", "lead inbox", "api", "customer relationship", "software spec", "brd", "webhook", "app source")),
    ("Astro Business / Consultations & Clients", ("consultation", "client chart", "client report", "reading report", "client intake", "birth details", "appointment")),
    ("Astro Business / Content & Marketing", ("instagram", "youtube", "blog", "content calendar", "social media", "campaign", "newsletter")),
    ("Astro Business / Finance & Operations", ("invoice", "business expense", "revenue", "profit", "payment receipt")),
]
MISC_RULES = [
    ("Personal & Misc / Photos & Videos", ("photo", "family video", "vacation photo", "wallpaper", "screenshot")),
    ("Personal & Misc / Bills & Receipts", ("bill", "receipt", "insurance", "electricity", "water bill", "tax")),
    ("Personal & Misc / IDs & Forms", ("aadhaar", "aadhar", "passport", "pan card", "voter id", "application form")),
    ("Personal & Misc / Travel", ("flight", "hotel booking", "itinerary", "boarding pass", "trip")),
]


@dataclass(frozen=True)
class Classification:
    category: str
    confidence: float
    reason: str


def clean(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[_\-./\\]+", " ", value)


def has_phrase(text: str, phrase: str) -> bool:
    p = clean(phrase).strip()
    if not p:
        return False
    return re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", text) is not None


def matches(text: str, cues: tuple[str, ...]) -> list[str]:
    return [cue for cue in cues if has_phrase(text, cue)]


def classify(filename: str, parent_path: str, content: str = "") -> Classification:
    """No network calls. Confident unmatched files are *never* silently assigned to a guessed project.

    Filename is more informative than folder and document text. Source folder names are
    used as context, not accepted as conclusive. Confidence is a heuristic, not an AI probability.
    """
    name = clean(filename)
    folder = clean(parent_path)
    body = clean(content[:120_000])
    evidence = {}
    for domain, cues in (("College", COLLEGE_CUES), ("Astro Business", ASTRO_CUES)):
        n = matches(name, cues)
        f = matches(folder, cues)
        b = matches(body, cues)
        score = 6 * len(n) + 2 * min(3, len(f)) + min(4, len(b))
        evidence[domain] = (score, n, f, b)

    college_score = evidence["College"][0]
    astro_score = evidence["Astro Business"][0]
    # Recognize project-specific file titles even when top-level words are absent.
    if not college_score and (has_phrase(name, "case study") or has_phrase(name, "assignment")):
        college_score += 6
    # A planet alone can be a name; use a strong signal only with a house/placement cue.
    for planet in PLANETS:
        if has_phrase(name, planet) and any(has_phrase(name, t) for t in ("house", "placement", "graha")):
            astro_score += 6
            break

    if max(college_score, astro_score) < 4 or (college_score > 0 and astro_score > 0 and abs(college_score - astro_score) < 3):
        return classify_misc(name)

    domain = "College" if college_score > astro_score else "Astro Business"
    dominant = max(college_score, astro_score)
    runner_up = min(college_score, astro_score)
    domain_reason = evidence[domain][1] or evidence[domain][2] or evidence[domain][3]
    basis = ", ".join(domain_reason[:3]) if domain_reason else "file context"
    confidence = min(0.98, 0.58 + dominant * 0.023 + max(0, dominant - runner_up) * 0.006)

    if domain == "College":
        rules = COLLEGE_RULES
        default = "College / Other College"
    else:
        # If we spot a house-related document about a specific planet, classify before other rules.
        for planet in PLANETS:
            if (has_phrase(name, planet) or has_phrase(body, planet)) and (
                has_phrase(name, "house") or has_phrase(name, "placement") or has_phrase(body, "house placement")
            ):
                return Classification(f"Astro Business / Planetary Placements / {planet}",
                                      max(confidence, 0.83), f"Planetary placement: {planet}")
        rules = ASTRO_RULES
        default = "Astro Business / Other Astro"

    best_category = default
    best_score = 0
    best_cues: list[str] = []
    for category, cues in rules:
        n = matches(name, cues)
        f = matches(folder, cues)
        b = matches(body, cues)
        score = 7 * len(n) + min(3, len(f)) + min(2, len(b))
        if score > best_score:
            best_category, best_score, best_cues = category, score, (n or f or b)

    if best_score:
        basis = ", ".join(best_cues[:3])
        confidence = min(0.99, confidence + 0.045)
    elif default.endswith("Other College") or default.endswith("Other Astro"):
        confidence = min(confidence, 0.77)

    return Classification(best_category, round(confidence, 2), f"Matched: {basis}")


def classify_misc(name: str) -> Classification:
    for cat, cues in MISC_RULES:
        found = matches(name, cues)
        if found:
            return Classification(cat, 0.77, f"Filename: {', '.join(found[:2])}")
    return Classification("Needs Review", 0.0, "No reliable project match — choose a folder manually")


def explain_classification(filename: str, parent_path: str, content: str, result: Classification) -> str:
    """Explain rule evidence, explicitly separating filename, path and document text.

    Explanation is based on the SAME cues and weights as classify(); not an AI score.
    """
    name, folder, body = clean(filename), clean(parent_path), clean(content[:120_000])
    lines = [f"Suggested category: {result.category}", f"Heuristic confidence: {result.confidence:.0%}",
             "This confidence is a rule-of-thumb score, NOT an AI probability.",
             "", "1. BROAD DOMAIN SIGNALS (filename / folder / contents)",
             "Broad category scores: +6 per filename match; +2 per folder match (max 3);",
             "+1 per document-content match (max 4). Special contextual rules may also apply.", ""]
    for domain, cues in (("College", COLLEGE_CUES), ("Astro Business", ASTRO_CUES)):
        n, f, b = (matches(part, cues) for part in (name, folder, body))
        score = 6*len(n) + 2*min(3, len(f)) + min(4,len(b))
        lines.append(f"{domain}: base score {score}")
        lines.append(f"  Filename: {', '.join(n[:8]) if n else '(none)'}")
        lines.append(f"  Folder path: {', '.join(f[:8]) if f else '(none)'}")
        lines.append(f"  Document text: {', '.join(b[:8]) if b else '(none)'}")
    lines.extend(["", "2. SPECIFIC DESTINATION RULES",
                  "Subcategory scores: +7 per filename match; +1 per folder match (max 3);",
                  "+1 per document-text match (max 2). Planetary-placement and misc rules differ."])
    relevant = next(((cat,cues) for cat,cues in (COLLEGE_RULES + ASTRO_RULES) if cat == result.category), None)
    if relevant:
        _, cues = relevant
        n, f, b = (matches(part, cues) for part in (name,folder,body))
        lines.extend([f"  Filename clues: {', '.join(n[:8]) if n else '(none)'}",
                      f"  Folder clues: {', '.join(f[:8]) if f else '(none)'}",
                      f"  Content clues: {', '.join(b[:8]) if b else '(none)'}"])
    elif "Planetary Placements" in result.category:
        lines.append("Special rule: a planet plus a house or placement cue in filename or text.")
    elif result.category == "Needs Review":
        lines.append("No clear category was found. Please manually select one before organizing.")
    elif result.category.startswith("Personal & Misc"):
        lines.append("Personal/Misc categories currently match FILENAME keywords only.")
    else:
        lines.append("General project category: no sufficiently specific subcategory cue found.")
    lines.extend(["", "3. WHAT WAS INSPECTED", "Filename: yes", "Parent folder path: yes",
                  f"Document text: {'available (' + str(len(content)) + ' characters)' if content else 'no extractable text or content reading disabled'}",
                  "Supported content: TXT, MD, CSV, PDF (text), DOCX, PPTX, XLSX.",
                  "Scanned-image PDFs, old DOC/PPT formats and other formats may have no text.",
                  "", "4. IMPORTANT", "Always review suggestions before organizing. Copy is the default.",
                  "This app does not use an AI model, train on your files or upload them."])
    return "\n".join(lines)
