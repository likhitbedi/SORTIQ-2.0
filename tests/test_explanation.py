from sortiq.taxonomy import classify, explain_classification
from sortiq.demo import create_demo
from sortiq.engine import scan


def test_explanation_identifies_filename_folder_content(tmp_path):
    base = tmp_path / 'quietfolder'; base.mkdir()
    (base/'Rahu_6th_House.txt').write_text('Rahu in house placements', encoding='utf-8')
    row = scan([base],tmp_path/'dest')[0]
    assert 'Filename:' in row.explanation
    assert 'Folder path:' in row.explanation
    assert 'Document text:' in row.explanation
    assert 'Rahu' in row.explanation or 'rahu' in row.explanation


def test_opaque_filename_uses_content_when_enough_clues():
    content = 'PGDM federal bank placement interview questions marketing management.'
    r=classify('Document123.pdf', 'Downloads', content)
    assert r.category == 'College / Placements & Interviews'
    explanation=explain_classification('Document123.pdf','Downloads',content,r)
    assert 'Document text' in explanation
    assert 'federal bank' in explanation


def test_manual_and_no_match(tmp_path):
    demo = create_demo(tmp_path/'demo')
    suggestions = scan([demo],tmp_path/'organized')
    assert any(s.category == 'Needs Review' for s in suggestions)
    assert all(s.explanation for s in suggestions)
