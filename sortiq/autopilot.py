"""SORTIQ 2.0: first-run profile, local semantic matching and safe automated scanning.

No document is sent to an external service. AI model downloads are opt-in. 
When no model is installed, a clearly-labelled vocabulary-only fallback is used.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .engine import Suggestion, app_data_dir, inside, iter_files
from .extractors import CONTENT_EXTS, get_text
from .vocabulary import Vocabulary, norm, valid_category

# Descriptions are written for semantic retrieval, rather than only keyword overlap.
# The first-run profile selects relevant branches, not a rigid global taxonomy.
DOMAINS = {
    "Education": {
        "triggers": "college university mba pgdm school student studies coursework assignment syllabus professor campus lectures education",
        "categories": {
            "College / Marketing & Branding": "marketing brand management brand equity marketing strategy consumer behavior research segmentation positioning targeting advertising retail trade marketing brand extension marketing mix",
            "College / Finance & Banking": "financial management accounting balance sheets banking investment budgets valuation loans corporate finance interest markets stocks financial ratios",
            "College / Operations & Analytics": "operations management supply chain inventory logistics project management statistics business analytics regression SPSS SAP data analysis process optimization",
            "College / Assignments & Projects": "college assignment semester project group work report submissions academic research coursework presentation project guidelines team deliverable",
            "College / Case Studies": "business case study industry analysis case discussion company problem management decisions exhibits competitive analysis",
            "College / Notes & Syllabus": "lecture notes textbook syllabus module topics reading material exam preparation faculty course outline learning objectives",
            "College / Placements & Interviews": "campus placement recruitment interview resume CV company application aptitude group discussion job offer Federal Bank selection HR round",
        },
    },
    "Astrology": {
        "triggers": "astro astrology jyotish kundali horoscope graha planets dasha zodiac lagna bhava nakshatra vedic consultation",
        "categories": {
            "Astro Business / Planetary Placements": "vedic astrology planetary placements houses first house second house sixth house rahu ketu jupiter saturn mars venus moon sun mercury effects in horoscope",
            "Astro Business / Horoscope Analysis": "kundali natal chart birth chart horoscope lagna ascendant navamsa d9 divisional charts dashas transits planetary positions prediction",
            "Astro Business / BPHS & Research": "brihat parashara hora shastra bphs jyotish shloka upagraha gulika mandi shadbala natural planetary relationships sanskrit research scripture",
            "Astro Business / Client Consultations": "astrology clients consultation booking appointments client notes readings question predictions guidance payment horoscope consultation reports",
            "Astro Business / Website & SEO": "astrology website wordpress hosting blog organic traffic seo keywords google search console indexing search engine analytics sitemap page ranking",
            "Astro Business / CRM & Software": "astrology crm contacts leads customers marketing automation sqlite python javascript sql wordpress api software developer database source code",
        },
    },
    "Software": {
        "triggers": "software developer program programming code python javascript sql github app website html css database automation vscode project",
        "categories": {
            "Software / Source Code & Databases": "programming source code python javascript typescript sql database tables schema application development code functions software scripts",
            "Software / Project Documentation": "technical documentation software requirements design specifications api architecture release notes implementation readme developer instructions",
        },
    },
    "Business": {
        "triggers": "business company office trade retailer retail sales distributor merchant revenue manager management entrepreneur startup",
        "categories": {
            "Work / Sales & Marketing": "sales performance trade marketing shopper marketing promotions retail distributors promoters incentives revenue targets visibility commercial business performance",
            "Work / Reports & Presentations": "company meeting report quarterly performance presentation business review KPI strategy sales reporting executive management slides",
            "Work / Administration & Finance": "business contracts receipts invoices purchase orders accounts taxation vendor payments administration compliance expenses",
        },
    },
    "Legal": {
        "triggers": "law lawyer legal courtroom advocate legislation statutes contract court litigation",
        "categories": {
            "Legal / Contracts": "legal agreement contract terms conditions clauses obligations vendor NDA confidentiality execution",
            "Legal / Cases & Research": "court case judgment law regulation litigation statutory precedent legal research hearing",
        },
    },
    "Creative": {
        "triggers": "design designer graphic photos photography video animation illustration fashion creative portfolio artwork",
        "categories": {
            "Creative / Designs & Graphics": "graphic design poster banners brochures illustrations creative design art digital visuals typography brand guidelines",
            "Creative / Video & Production": "video production editing animation film scripts storyboards audio cinematography reels clips footage",
        },
    },
    "Health": {
        "triggers": "doctor hospital medical medicine healthcare health patient clinical nursing physician research",
        "categories": {
            "Healthcare / Clinical Research": "clinical study patient treatment disease diagnosis medicines medical research healthcare guidelines",
            "Healthcare / Administration": "hospital operations patient intake records appointments scheduling billing insurance healthcare management",
        },
    },
}

GENERAL = {
    "Personal / Bills & Receipts": "personal invoice bill receipt payment electricity water credit card purchases utility expenses statement",
    "Personal / Forms & IDs": "personal application form identification passport government documents certificate voter id personal information",
    "Media / Images": "photographs photos screenshots jpeg jpg png images pictures graphics camera",
    "Media / Video & Audio": "videos movies mp4 recordings sound music mp3 wav audio",
    "Archives / Compressed Files": "archived compressed zip rar 7z tar backup file bundle",
}

# User descriptions remain local, and categories are also configurable after setup.
def create_profile(description: str, model_enabled: bool = False) -> dict:
    description = re.sub(r"\s+", " ", description.strip())
    if len(description) < 18:
        raise ValueError("Tell SORTIQ more about your work, studies and types of documents (at least 18 characters).")
    if len(description) > 6000:
        raise ValueError("Keep the initial description under 6,000 characters.")
    low = norm(description)
    selected: dict[str, str] = {}
    for domain in DOMAINS.values():
        terms = domain["triggers"].split()
        # Multiple short words should not match inside unrelated words.
        hits = sum(bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", low)) for term in terms)
        if hits >= 1:
            selected.update(domain["categories"])
    # No manual taxonomy needed if the user's prose does not match built-in industries.
    # A generic subject inferred from their work is used as a candidate; users can edit it.
    if not selected:
        subject = re.search(r"\b(?:work(?:ing)? (?:in|with|on)|study(?:ing)?|focus(?:ing)? on|research(?:ing)?)\s+([\w &\-]{3,55})", low)
        label = " ".join(subject.group(1).split()[:5]).title() if subject else "My Projects"
        label = re.sub(r"[<>:\"/\\|?*.]", "", label).strip() or "My Projects"
        selected[f"Work / {label[:48]}"] = description[:700]
    selected.update(GENERAL)
    for key in selected: valid_category(key)
    return {"description": description, "categories": selected, "ai_enabled": bool(model_enabled), "created_at": int(time.time()), "version": 2}


def profile_path() -> Path:
    return app_data_dir() / "autopilot-profile.json"


def load_profile(path: Path | None = None) -> dict | None:
    p = path or profile_path()
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict) or not obj.get("description") or not isinstance(obj.get("categories"), dict):
            return None
        for c in obj["categories"]: valid_category(c)
        return obj
    except (OSError, ValueError, TypeError, KeyError):
        return None


def save_profile(profile: dict, path: Path | None = None) -> None:
    p = path or profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(".tmp")
    t.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    t.replace(p)


def register_profile(profile: dict):
    # Re-use V1's verified category-path validation and move/undo engine.
    vocab = Vocabulary()
    for cat in profile["categories"]:
        vocab._register(cat)


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z\d]+", norm(s)) if len(w) > 2}


def _phrases(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:\s+[a-z0-9]+){1,3}", norm(s)))


def _keywords(label: str, description: str) -> set[str]:
    excluded = {"and", "the", "of", "with", "from", "into", "work", "reports", "documents", "files", "related", "general", "other"}
    return (_words(description) | _words(label)) - excluded


@dataclass
class AutoDecision:
    category: str
    score: float
    status: str
    explanation: str
    method: str
    candidate: str = ""


class LocalSemanticModel:
    """Optional local ONNX embedding model. Downloads weights only with express permission."""
    MODEL = "BAAI/bge-small-en-v1.5"

    def __init__(self, consent_to_download: bool = False, model_dir: Path | None = None):
        self.consent_to_download = consent_to_download
        self.model_dir = model_dir or (app_data_dir() / "models")
        self.engine = None
        self.error = ""

    def start(self) -> bool:
        if not self.consent_to_download:
            self.error = "Local AI has not been enabled in the first-run privacy settings"
            return False
        try:
            from fastembed import TextEmbedding
            # A first-run download is permitted only if the user opted in.
            # local_files_only prevents silently contacting Hugging Face on later runs.
            marker = self.model_dir / ".sortiq-model-ready"
            try:
                self.engine = TextEmbedding(model_name=self.MODEL, cache_dir=str(self.model_dir),
                                            local_files_only=marker.exists())
            except Exception:
                # With the user's consent, retry a damaged or incomplete cache online.
                self.engine = TextEmbedding(model_name=self.MODEL, cache_dir=str(self.model_dir),
                                            local_files_only=False)
            self.model_dir.mkdir(parents=True, exist_ok=True)
            marker.write_text(self.MODEL, encoding="utf-8")
            return True
        except Exception as exc:
            self.engine = None
            self.error = f"Local AI unavailable: {type(exc).__name__}: {exc}"
            return False

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.engine is None:
            raise RuntimeError("AI model is not ready")
        return [list(map(float, v)) for v in self.engine.embed(texts, batch_size=16)]


def _cosine(u, v) -> float:
    n = sum(a*b for a,b in zip(u,v))
    d = math.sqrt(sum(a*a for a in u)*sum(b*b for b in v))
    return max(-1.0, min(1.0, n/d)) if d else 0.0


def _chunks(text: str, size: int = 1050, max_parts: int = 4) -> list[str]:
    # Sample beginning, middle, and end rather than truncating all long documents to the cover page.
    text = re.sub(r"\s+", " ", text.strip())
    if not text: return []
    if len(text) <= size: return [text]
    positions = [int(i*(len(text)-size)/(max_parts-1)) for i in range(max_parts)]
    return [text[p:p+size] for p in positions]


class HybridClassifier:
    """Subject classification with explainability and conservative auto-routing.

    Scores are similarity/ranking heuristics, NOT statistical probabilities.
    """
    def __init__(self, profile: dict, model: LocalSemanticModel | None = None):
        self.profile = profile
        self.model = model if model and model.engine is not None else None
        self.cat_desc = profile["categories"]
        self.cat_terms = {k: _keywords(k, v) for k,v in self.cat_desc.items()}
        self.vectors: dict[str, list[float]] = {}
        if self.model:
            payload = [f"Represent this document category: {k.replace('/', ' ')}. {v}" for k,v in self.cat_desc.items()]
            for name, vector in zip(self.cat_desc, self.model.embed(payload)):
                self.vectors[name] = vector

    def classify(self, path: Path, text: str, parser_note: str | None = None,
                 cached_vectors: list[list[float]] | None = None) -> AutoDecision:
        ext = path.suffix.lower()
        if parser_note and not text and ext in CONTENT_EXTS:
            return AutoDecision("Needs Review", 0.0, "Review", f"Unreadable or protected document: {parser_note}", "parser")
        if ext in {".exe", ".msi", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".lnk", ".url"}:
            return AutoDecision("Needs Review", 0.0, "Review", "Program/shortcut files aren't classified or moved automatically.", "safety")
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"} and not text:
            return AutoDecision("Media / Images", .99, "Ready", "Media recognized by file type. This is not image-content AI.", "file-type")
        if ext in {".mp4", ".mov", ".avi", ".mp3", ".wav", ".m4a", ".mkv"} and not text:
            return AutoDecision("Media / Video & Audio", .99, "Ready", "Media recognized by file type. Audio/video content was not analyzed.", "file-type")
        if ext in {".zip", ".rar", ".7z", ".tar", ".gz"} and not text:
            return AutoDecision("Archives / Compressed Files", .99, "Ready", "Archive recognized by file type; archive contents weren't inspected.", "file-type")
        if ext in CONTENT_EXTS and not text.strip() and path.suffix.lower() not in {".txt", ".md", ".csv"}:
            return AutoDecision("Needs Review", 0, "Review", "No extractable document text. Scanned images, encrypted and unsupported formats need additional processing.", "unreadable")
        if not text.strip() and not path.stem.strip():
            return AutoDecision("Needs Review", 0, "Review", "No readable text", "empty")
        body = norm(text[:42000])
        filename = norm(path.stem)
        # Avoid treating source folder names as decisive: Downloads contains mixed content.
        folder = norm(path.parent.name)
        doc_words = _words(body)
        filename_words = _words(filename)
        folder_words = _words(folder)
        lexical: dict[str, float] = {}
        matched: dict[str, list[str]] = {}
        for cat, terms in self.cat_terms.items():
            content_hits = terms & doc_words
            file_hits = terms & filename_words
            folder_hits = terms & folder_words
            hits = sorted(content_hits | file_hits)
            matched[cat] = hits[:14]
            # Distinct matches, capped to prevent long-file keyword repetition dominating.
            lexical[cat] = min(len(content_hits), 9)*.055 + min(len(file_hits), 6)*.09 + min(len(folder_hits), 3)*.008
            lexical[cat] = min(1.0, lexical[cat])
        semantic: dict[str, float] = {}
        if self.model and self.vectors and (body or filename):
            chunks = _chunks(text, max_parts=4)
            # A filename is evidence, but cannot drown out actual document contents.
            embeddings = cached_vectors if cached_vectors is not None else self.model.embed(chunks or [path.stem])
            for cat, vector in self.vectors.items():
                sims = sorted((_cosine(vec, vector) for vec in embeddings), reverse=True)
                semantic[cat] = .72*sims[0] + .28*(sum(sims)/len(sims))
        scores = {}
        for cat in self.cat_desc:
            scores[cat] = (semantic[cat]*.78 + lexical[cat]*.22) if semantic else lexical[cat]
        ranked = sorted(scores, key=scores.get, reverse=True)
        best = ranked[0]
        runner = ranked[1] if len(ranked)>1 else None
        top, second = scores[best], (scores[runner] if runner else 0)
        margin = top-second
        has_content = bool(text.strip())
        # Release thresholds are conservative STARTING VALUES; calibrate on labeled examples.
        if semantic:
            ready = has_content and top >= .49 and margin >= .065 and (lexical[best] >= .08 or top >= .61)
            label = "Local AI + keyword evidence"
        else:
            # Offline fallback is not presented as an AI result.
            ready = lexical[best] >= .26 and margin >= .16 and len(matched[best]) >= 3
            label = "Keywords only (AI unavailable)"
        # Generic categories require stronger evidence to avoid dumping most text into them.
        if best in GENERAL and ext in CONTENT_EXTS and not matched[best]: ready = False
        reason = (f"Method: {label}\nTop suggestion: {best}\nScore: {top:.3f} | runner-up: {runner or 'none'} ({second:.3f})\n"
                  f"Margin: {margin:.3f}\nMatched terms: {', '.join(matched[best]) or 'none'}\n"
                  f"Readable content: {'yes' if has_content else 'no'}\n\n"
                  "Scores are uncalibrated relevance measures, not probabilities.\n"
                  "The program does not send your document text to a cloud provider.")
        if not ready:
            reason += "\n\nLeft untouched: insufficient category evidence or a close competing match."
        return AutoDecision(best if ready else "Needs Review", round(top, 3), "Ready" if ready else "Review", reason, label, best)


class AnalysisCache:
    """Local performance cache keyed by size+mtime. User can delete it anytime."""
    def __init__(self, path: Path | None = None):
        self.path = path or (app_data_dir() / "analysis-cache.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS extracted (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, text TEXT, note TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS embeddings (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, model TEXT, vectors TEXT)")

    def get_vectors(self, path: Path, size: int, mtime_ns: int, model_name: str) -> list[list[float]] | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT vectors FROM embeddings WHERE path=? AND size=? AND mtime_ns=? AND model=?",
                             (str(path),size,mtime_ns,model_name)).fetchone()
        return json.loads(row[0]) if row else None

    def put_vectors(self, path: Path, size: int, mtime_ns: int, model_name: str,
                    vectors: list[list[float]]):
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO embeddings (path,size,mtime_ns,model,vectors) VALUES (?,?,?,?,?)",
                       (str(path),size,mtime_ns,model_name,json.dumps(vectors)))

    def extract(self, path: Path, size: int, mtime_ns: int) -> tuple[str, str | None]:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT text,note FROM extracted WHERE path=? AND size=? AND mtime_ns=?",
                             (str(path), size, mtime_ns)).fetchone()
        if row is not None:
            return row[0], row[1] or None
        text, note = get_text(path) if size <= 55*1024*1024 else ("", "File exceeds 55 MB text extraction limit")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO extracted (path,size,mtime_ns,text,note) VALUES (?,?,?,?,?)",
                       (str(path), size, mtime_ns, text[:42000], note))
        return text, note


def auto_scan(roots: Iterable[Path], destination: Path, classifier: HybridClassifier,
              progress: Callable[[int,str],None] | None = None,
              cancel: threading.Event | None = None,
              cache: AnalysisCache | None = None,
              max_files: int = 35000) -> list[Suggestion]:
    rows: list[Suggestion] = []
    cache = cache or AnalysisCache()
    for source in iter_files(roots, destination, recursive=True, cancel=cancel):
        if cancel is not None and cancel.is_set(): break
        if len(rows) >= max_files: raise RuntimeError("Too many files; select smaller folders")
        try:
            st = source.stat()
            text, note = cache.extract(source, st.st_size, st.st_mtime_ns)
            cached_vectors = None
            if classifier.model and (text.strip() or source.stem.strip()) and source.suffix.lower() in CONTENT_EXTS:
                cached_vectors = cache.get_vectors(source,st.st_size,st.st_mtime_ns,classifier.model.MODEL)
                if cached_vectors is None:
                    cached_vectors = classifier.model.embed(_chunks(text, max_parts=4) or [source.stem])
                    cache.put_vectors(source,st.st_size,st.st_mtime_ns,classifier.model.MODEL,cached_vectors)
            outcome = classifier.classify(source, text, note, cached_vectors=cached_vectors)
            rows.append(Suggestion(source=source, category=outcome.category, confidence=outcome.score,
                                   reason=outcome.method, size=st.st_size, status=outcome.status,
                                   excerpt=text[:350], error=note or "", explanation=outcome.explanation,
                                   mtime_ns=st.st_mtime_ns))
        except (PermissionError, OSError, ValueError) as exc:
            rows.append(Suggestion(source=source, category="Needs Review", confidence=0,
                                   reason=f"Unreadable: {type(exc).__name__}", size=0,
                                   status="Review", error=str(exc)))
        if progress and len(rows) % 10 == 0: progress(len(rows), source.name)
    if progress: progress(len(rows), "Complete")
    return rows
