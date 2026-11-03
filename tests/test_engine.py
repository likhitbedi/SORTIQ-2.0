"""Run: python -m pytest -q"""
import os
from pathlib import Path

import pytest

from sortiq.demo import create_demo
from sortiq.engine import (
    History, Suggestion, choose_destination, inside, iter_files, override,
    scan, sort_files, undo_last,
)
from sortiq.taxonomy import CATEGORY_TREE, classify


def test_demo_recognizes_college_and_astro(tmp_path):
    source = create_demo(tmp_path / "source")
    rows = scan([source], tmp_path / "library")
    mapping = {row.source.name: row for row in rows}
    assert len(rows) >= 10  # additional real Office-format examples appear when readers are installed
    assert mapping["Federal_Bank_Interview_Questions.txt"].category == "College / Placements & Interviews"
    assert mapping["GoPro_Case_Study.txt"].category == "College / Case Studies"
    assert mapping["Prime_Marketing_Attendance.csv"].category == "College / Attendance & Admin"
    assert mapping["Rahu_in_6th_House_Research.md"].category.endswith("/ Rahu")
    assert mapping["GrahasWithLikhit_SEO_Keywords.txt"].category == "Astro Business / Website & SEO"
    assert mapping["Unknown_Document_8371.txt"].status == "Review"
    if "Semester_Notes.xlsx" in mapping:
        assert mapping["Semester_Notes.xlsx"].category == "College / Subjects / Brand Management"
    if "GrahasWithLikhit_SEO_Plan.pptx" in mapping:
        assert mapping["GrahasWithLikhit_SEO_Plan.pptx"].category == "Astro Business / Website & SEO"
    if "BPHS_Reference_Summary.pdf" in mapping:
        assert mapping["BPHS_Reference_Summary.pdf"].category == "Astro Business / BPHS & Jyotish Research"
    assert sum(r.status == "Ready" for r in rows) == len(rows) - 1


def test_copy_keeps_original_then_undo_deletes_copy(tmp_path):
    source = create_demo(tmp_path / "input")
    output = tmp_path / "output"
    history = History(tmp_path / "db" / "history.sqlite3")
    rows = scan([source], output)
    result = sort_files([r for r in rows if r.status == "Ready"], output, [source], history, "copy")
    assert result.sorted == len(rows) - 1 and not result.failures
    assert (source / "Random Downloads" / "Federal_Bank_Interview_Questions.txt").exists()
    expected = output / "College" / "Placements & Interviews" / "Federal_Bank_Interview_Questions.txt"
    assert expected.exists()
    undone, issues = undo_last(history)
    assert undone == len(rows) - 1 and not issues
    assert not expected.exists()
    assert (source / "Random Downloads" / "Federal_Bank_Interview_Questions.txt").exists()


def test_move_undo_and_collision_renames(tmp_path):
    source, output = tmp_path / "input", tmp_path / "out"
    source.mkdir()
    f = source / "Federal_Bank_Interview.txt"
    f.write_text("PGDM placement notes v1", encoding="utf-8")
    history = History(tmp_path / "history.sqlite3")
    first = scan([source], output)[0]
    target = output / "College" / "Placements & Interviews" / f.name
    target.parent.mkdir(parents=True)
    target.write_text("Already here different contents", encoding="utf-8")
    result = sort_files([first], output, [source], history, "move")
    assert result.sorted == 1 and not result.failures
    assert not f.exists()
    renamed = target.with_name("Federal_Bank_Interview (2).txt")
    assert renamed.exists() and target.read_text() == "Already here different contents"
    undone, issues = undo_last(history)
    assert undone == 1 and issues == ()
    assert f.read_text() == "PGDM placement notes v1"
    assert target.exists() and not renamed.exists()


def test_duplicate_skip_never_overwrites(tmp_path):
    source, dest = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    f = source / "Rahu_in_6th_House.md"
    f.write_text("astrology reference", encoding="utf-8")
    row = scan([source], dest)[0]
    hist = History(tmp_path / "history.sqlite3")
    first = sort_files([row], dest, [source], hist)
    second = sort_files([row], dest, [source], hist)
    assert first.sorted == 1 and second.sorted == 0 and second.duplicates == 1
    assert f.exists()


def test_manual_override_and_review_protection(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    unknown = source / "0000_random.txt"
    unknown.write_text("no special signals", encoding="utf-8")
    output = tmp_path / "lib"
    rows = scan([source], output)
    history = History(tmp_path / "h.db")
    assert rows[0].status == "Review"
    result = sort_files(rows, output, [source], history, mode="move")
    assert result.sorted == 0 and result.skipped == 1 and unknown.exists()
    chosen = override(rows[0], "College / Assignments")
    result = sort_files([chosen], output, [source], history, mode="copy")
    assert result.sorted == 1 and (output / "College" / "Assignments" / unknown.name).exists()


def test_external_source_rejected(tmp_path):
    source = tmp_path / "approved"
    source.mkdir()
    external = tmp_path / "outside"
    external.mkdir()
    f = external / "Federal_Bank_Interview.txt"
    f.write_text("PGDM", encoding="utf-8")
    row = scan([external], tmp_path / "out")[0]
    history = History(tmp_path / "history.sqlite3")
    result = sort_files([row], tmp_path / "out", [source], history, mode="move")
    assert result.sorted == 0 and result.failures and f.exists()


def test_output_nested_inside_input_is_excluded(tmp_path):
    source = tmp_path / "Documents"
    output = source / "SORTIQ Library"
    output.mkdir(parents=True)
    (output / "old.txt").write_text("ignore me")
    (source / "Federal_Bank_Interview.txt").write_text("PGDM")
    files = list(iter_files([source], output))
    assert len(files) == 1 and files[0].name == "Federal_Bank_Interview.txt"


def test_changed_destination_blocks_undo(tmp_path):
    source, output = tmp_path / "in", tmp_path / "out"
    source.mkdir()
    f = source / "Federal_Bank_Interview.txt"
    f.write_text("PGDM", encoding="utf-8")
    history = History(tmp_path / "h.db")
    row = scan([source], output)[0]
    assert sort_files([row], output, [source], history, mode="move").sorted == 1
    moved = output / "College" / "Placements & Interviews" / f.name
    moved.write_text("edited after sorting", encoding="utf-8")
    n, errors = undo_last(history)
    assert n == 0 and errors and not f.exists() and moved.exists()


def test_output_file_inside_untrusted_category_not_allowed(tmp_path):
    root = tmp_path / "src"
    root.mkdir()
    f = root / "x.txt"
    f.write_text("test")
    h = History(tmp_path / "h.db")
    suggestion = Suggestion(f, "../../escape", 1, "Injected category", 4)
    result = sort_files([suggestion], tmp_path / "out", [root], h)
    assert result.sorted == 0 and result.failures and f.exists()


def test_exact_keywords_not_substrings():
    assert classify("PPT_Federal_Bank.pptx", "Downloads").category == "College / Placements & Interviews"
    assert classify("Rahu_12th_House.pdf", "Downloads").category.endswith("/ Rahu")
    assert classify("particular.txt", "Downloads").category == "Needs Review"


def test_selected_folder_beneath_appdata_is_scannable(tmp_path):
    # Windows pytest temp folders are often beneath AppData/Local/Temp.
    # A user-selected source there must not be rejected merely because the
    # parent path contains AppData.
    source = tmp_path / "AppData" / "Local" / "Temp" / "selected"
    source.mkdir(parents=True)
    f = source / "Federal_Bank_Interview.txt"
    f.write_text("PGDM campus placement questions", encoding="utf-8")
    rows = scan([source], tmp_path / "organized")
    assert len(rows) == 1
    assert rows[0].source == f
