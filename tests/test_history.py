"""Offline tests for run history persistence."""
import json

import pytest

from marketpulse.history import delete_run, list_runs, load_run, save_run
from marketpulse.schemas import CrewResult, ScoutInput

INPUTS = ScoutInput(business_idea="pet grooming", city="Austin", target_customer="dog owners",
                    known_competitors="Petco")


def _result(deck=None, warnings=None):
    return CrewResult(report_markdown="# Report\n\nbody", pitch_deck_markdown=deck,
                      report_path="x/report.md", warnings=warnings or [])


def test_save_and_load_roundtrip(tmp_path):
    rid = save_run(INPUTS, _result(deck="## Slide 1", warnings=["w1"]), True, True, 61.234, tmp_path)
    inputs, result, meta = load_run(rid, tmp_path)
    assert inputs == INPUTS
    assert result.report_markdown == "# Report\n\nbody"
    assert result.pitch_deck_markdown == "## Slide 1"
    assert result.warnings == ["w1"]
    assert meta.run_id == rid and meta.hierarchical and meta.pitch_deck
    assert meta.status == "done" and meta.elapsed_seconds == 61.2
    assert json.loads((tmp_path / rid / "meta.json").read_text(encoding="utf-8"))["city"] == "Austin"


def test_no_deck_file_when_absent(tmp_path):
    rid = save_run(INPUTS, _result(), False, False, 1, tmp_path)
    assert not (tmp_path / rid / "pitch_deck.md").exists()
    assert load_run(rid, tmp_path)[1].pitch_deck_markdown is None


def test_list_runs_newest_first_and_skips_corrupt(tmp_path):
    (tmp_path / "20200101-000000-aaaa").mkdir()  # no meta.json
    bad = tmp_path / "20200102-000000-bbbb"
    bad.mkdir()
    (bad / "meta.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "not-a-run").mkdir()
    ids = [save_run(INPUTS, _result(), False, False, 1, tmp_path) for _ in range(3)]
    runs = list_runs(tmp_path)
    assert {r.run_id for r in runs} == set(ids)
    assert [r.created_at for r in runs] == sorted((r.created_at for r in runs), reverse=True)


def test_list_runs_missing_dir(tmp_path):
    assert list_runs(tmp_path / "nope") == []


def test_delete_run(tmp_path):
    rid = save_run(INPUTS, _result(), False, False, 1, tmp_path)
    assert delete_run(rid, tmp_path) is True
    assert not (tmp_path / rid).exists()
    assert delete_run(rid, tmp_path) is False
    assert list_runs(tmp_path) == []


def test_load_unknown_run(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_run("20200101-000000-aaaa", tmp_path)


def test_load_corrupt_report_missing(tmp_path):
    rid = save_run(INPUTS, _result(), False, False, 1, tmp_path)
    (tmp_path / rid / "report.md").unlink()
    with pytest.raises(ValueError):
        load_run(rid, tmp_path)


@pytest.mark.parametrize("bad", ["../x", "..", "../../etc", "20200101-000000-aaaa/..", "20200101-000000-AAAA",
                                 "", "a/b", "..\\x", "20200101-000000-aaaa\n", None, 5])
def test_path_traversal_blocked(tmp_path, bad):
    runs = tmp_path / "runs"
    runs.mkdir()
    victim = tmp_path / "x"
    victim.mkdir()
    (victim / "meta.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        load_run(bad, runs)
    assert delete_run(bad, runs) is False
    assert victim.exists()
