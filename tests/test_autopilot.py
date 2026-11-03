from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from sortiq.autopilot import (AnalysisCache, HybridClassifier, LocalSemanticModel, _chunks,
                              _cosine, auto_scan, create_profile, load_profile, save_profile,
                              register_profile)
from sortiq.engine import History, sort_files, undo_last


def test_profile_from_free_text_and_saved(tmp_path):
    p = create_profile("I study MBA marketing and finance in college and operate an astrology consultancy with a CRM and SEO website.")
    assert "College / Marketing & Branding" in p["categories"]
    assert "Astro Business / Horoscope Analysis" in p["categories"]
    assert "Astro Business / CRM & Software" in p["categories"]
    assert p["ai_enabled"]
    fp=tmp_path / "profile.json"
    save_profile(p, fp)
    assert load_profile(fp)["description"] == p["description"]


def test_short_profile_rejected():
    with pytest.raises(ValueError):create_profile("hi")


def test_custom_unknown_profession():
    p=create_profile("I work in paleontology documenting fossil specimens and mineral strata.")
    assert any("paleontology" in c.lower() for c in p["categories"])


def test_lexical_strong_content_matches_even_random_filename(tmp_path):
    p=create_profile("I am an MBA college student studying marketing, finance, banking and analytics.")
    model=HybridClassifier(p)
    result=model.classify(tmp_path / "1234.txt", "Marketing brand equity consumer segmentation targeting branding advertising retail research brand positioning customer campaigns")
    assert result.category == "College / Marketing & Branding"
    assert result.status == "Ready"
    assert "Keywords only" in result.explanation


def test_ambiguous_or_empty_is_not_misfiled(tmp_path):
    p=create_profile("I study an MBA at college and manage astrology consultations.")
    model=HybridClassifier(p)
    result=model.classify(tmp_path / "abc.txt", "Hello world, some miscellaneous notes.")
    assert result.status == "Review"
    assert result.category == "Needs Review"


def test_unreadable_pdf_and_programs_never_auto_file(tmp_path):
    p=create_profile("I study MBA finance and run astrology research with customer documents.")
    model=HybridClassifier(p)
    assert model.classify(tmp_path/"research.pdf", "", "Encrypted PDF").status == "Review"
    assert model.classify(tmp_path/"installer.exe", "marketing brand research").status == "Review"


def test_media_metadata_does_not_claim_content_analysis(tmp_path):
    p=create_profile("I study MBA college marketing and run astrology research.")
    model=HybridClassifier(p)
    out=model.classify(tmp_path/"IMG_001.jpeg", "")
    assert out.category=="Media / Images"
    assert "not image-content AI" in out.explanation


def test_autoscan_and_copy_do_not_touch_uncertain_originals(tmp_path):
    src=tmp_path/"source";src.mkdir()
    good=src/"c7342.txt"
    good.write_text("Market segmentation brand equity consumer behaviour campaign advertising marketing mix targeting branding brand strategy consumer analytics retail",encoding="utf8")
    unclear=src/"unknown.txt";unclear.write_text("unrelated notes on a desk",encoding="utf8")
    library=tmp_path/"library"
    profile=create_profile("MBA college student studying marketing and finance.")
    register_profile(profile)
    rows=auto_scan([src],library,HybridClassifier(profile),cache=AnalysisCache(tmp_path/"cache.db"))
    assert len(rows)==2
    assert any(r.status=="Ready" for r in rows)
    h=History(tmp_path/"history.db")
    result=sort_files([r for r in rows if r.status=="Ready"],library,[src],h,"copy")
    assert result.sorted>=1
    assert good.exists() and unclear.exists()
    assert not any(p.name=="unknown.txt" for p in library.rglob("*"))
    undone, errors=undo_last(h)
    assert undone==result.sorted and not errors
    assert good.exists()


def test_source_modified_after_scan_rejected(tmp_path):
    src=tmp_path/"src";src.mkdir()
    file=src/"marketing.txt"
    file.write_text("marketing brand strategy segmentation consumer behaviour research",encoding="utf8")
    p=create_profile("college MBA marketing studies and finance coursework")
    register_profile(p)
    rows=auto_scan([src],tmp_path/"dest",HybridClassifier(p),cache=AnalysisCache(tmp_path/"cache.db"))
    assert rows[0].status=="Ready"
    file.write_text("marketing brand strategy segmentation consumer behaviour research  ",encoding="utf8")
    out=sort_files(rows,tmp_path/"dest",[src],History(tmp_path/"history.db"),"copy")
    assert out.sorted==0 and len(out.failures)==1


def test_chunk_sampling_across_long_documents():
    parts=_chunks("abc "+("first "+"middle "+"last ")*1000)
    assert len(parts)==4 and all(len(p)<=1050 for p in parts)


def test_cosine_vectors():
    assert abs(_cosine([1,0],[1,0])-1)<1e-8
    assert abs(_cosine([1,0],[0,1]))<1e-8

class FakeEmbed:
    MODEL = "fake-test-model"
    engine = True
    def __init__(self): self.calls=0
    def embed(self, texts):
        self.calls += 1
        # deterministic stand-in for inference; validates integration, not model accuracy.
        def vec(t):
            low=t.lower()
            return [float("marketing" in low or "brand" in low),
                    float("astrology" in low or "rahu" in low or "kundali" in low),
                    float("finance" in low or "bank" in low)]
        return [vec(t) for t in texts]


def test_semantic_model_path_with_cached_embeddings(tmp_path):
    p = create_profile("MBA student studying marketing and finance and Vedic astrology consultations.")
    register_profile(p)
    embed = FakeEmbed()
    cls = HybridClassifier(p, embed)
    folder=tmp_path/"root";folder.mkdir()
    f=folder/"doc123.txt";f.write_text("Brand equity and marketing customer segmentation positioning brand.",encoding="utf-8")
    cache=AnalysisCache(tmp_path/"cache.sqlite3")
    first=auto_scan([folder],tmp_path/"out",cls,cache=cache)
    counts=embed.calls
    second=auto_scan([folder],tmp_path/"out",cls,cache=cache)
    assert counts==embed.calls
    assert first[0].category==second[0].category
    assert "Local AI" in first[0].explanation

def test_missing_bundled_ai_does_not_download(tmp_path):
    model_dir=tmp_path/"missing-model"
    model=LocalSemanticModel(model_dir=model_dir)
    assert model.start() is False
    assert not model_dir.exists()
    assert "Reinstall" in model.error


def test_bundled_ai_uses_specific_model_path_offline(tmp_path, monkeypatch):
    import fastembed
    from sortiq.autopilot import load_profile
    import json
    from pathlib import Path
    folder=tmp_path/"ai-model"
    folder.mkdir()
    (folder/"placeholder").write_text("dummy")
    calls=[]
    class FakeModel:
        def __init__(self, **kwargs): calls.append(kwargs)
        def embed(self, texts, **kwargs):
            yield [1.0]*384
    monkeypatch.setattr(fastembed, "TextEmbedding", FakeModel)
    model=LocalSemanticModel(model_dir=folder)
    assert model.start() is True, model.error
    assert calls==[{"model_name":model.MODEL,
                    "specific_model_path":str(folder.resolve()),
                    "local_files_only":True}]
    assert len(model.embed(["hello"])[0])==384
    profile=create_profile("I am a college student studying marketing, branding and finance")
    profile["ai_enabled"]=False
    file=tmp_path/"profile.json"
    file.write_text(json.dumps(profile),encoding="utf-8")
    assert load_profile(file)["ai_enabled"] is True
