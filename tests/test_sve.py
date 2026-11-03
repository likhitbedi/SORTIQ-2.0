from pathlib import Path
from sortiq.vocabulary import Vocabulary
from sortiq.engine import scan, History, sort_files

def test_sve_local_and_safe(tmp_path):
    v=Vocabulary()
    v.set_subject('College / Marketing','segmentation, branding, positioning')
    v.set_subject('Astro Business / Research','rahu, nakshatra, shadbala')
    db=tmp_path/'subjects.json';v.save(db)
    v=Vocabulary.load(db)
    source=tmp_path/'in';source.mkdir()
    (source/'untitled.txt').write_text('segmentation, branding and positioning')
    (source/'unknown.txt').write_text('miscellaneous')
    output=tmp_path/'out'
    rows=scan([source],output,vocabulary=v)
    assert rows[0].category=='College / Marketing'
    assert rows[1].category=='Needs Review'
    assert all(x.source.exists() for x in rows)
    result=sort_files(rows,output,[source],History(tmp_path/'h.db'),mode='copy')
    assert result.sorted==1
    assert (output/'College'/'Marketing'/'untitled.txt').exists()
    assert (source/'untitled.txt').exists()

def test_unsafe_categories():
    import pytest
    v=Vocabulary()
    for bad in ['../escape','/tmp','CON','College / ../Escape','College / Foo:Bar']:
        with pytest.raises(ValueError):v.set_subject(bad,'sample, phrase')
