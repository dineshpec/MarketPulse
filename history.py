"""Saved research runs on disk (no Streamlit). Layout: runs/<run_id>/{meta.json, report.md, pitch_deck.md}."""
from __future__ import annotations

import json
import re
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .schemas import CrewResult, ScoutInput

RUNS_DIR = Path(__file__).resolve().parent / "runs"
# e.g. 20261017-153045-ab12. Strict on purpose: the id becomes a folder name (blocks path traversal).
RUN_ID_RE = re.compile(r"\d{8}-\d{6}-[0-9a-f]{4}")


class RunMeta(BaseModel):
    run_id: str
    created_at: str  # ISO 8601
    business_idea: str
    city: str
    target_customer: str
    known_competitors: str = ""
    hierarchical: bool = False
    pitch_deck: bool = False
    warnings: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    status: str = "done"


def _valid_id(run_id) -> bool:
    return isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None


def _run_path(run_id, runs_dir: Path | None) -> Path | None:
    """Folder for run_id, or None if the id is malformed or escapes runs_dir."""
    if not _valid_id(run_id):
        return None
    base = Path(runs_dir or RUNS_DIR).resolve()
    p = (base / run_id).resolve()
    return p if p.parent == base else None


def save_run(inputs: ScoutInput, result: CrewResult, hierarchical: bool, pitch_deck: bool,
             elapsed_seconds: float, runs_dir: Path | None = None) -> str:
    """Write a finished run to disk and return its run_id."""
    base = Path(runs_dir or RUNS_DIR)
    base.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    while True:
        run_id = f"{now:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
        folder = base / run_id
        try:
            folder.mkdir()
            break
        except FileExistsError:
            continue
    meta = RunMeta(
        run_id=run_id, created_at=now.isoformat(timespec="seconds"),
        business_idea=inputs.business_idea, city=inputs.city,
        target_customer=inputs.target_customer, known_competitors=inputs.known_competitors,
        hierarchical=hierarchical, pitch_deck=pitch_deck, warnings=list(result.warnings),
        elapsed_seconds=round(float(elapsed_seconds), 1), status="done")
    (folder / "report.md").write_text(result.report_markdown, encoding="utf-8")
    if result.pitch_deck_markdown:
        (folder / "pitch_deck.md").write_text(result.pitch_deck_markdown, encoding="utf-8")
    # meta.json last: a folder without it is treated as incomplete and skipped by list_runs.
    (folder / "meta.json").write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    return run_id


def _read_meta(folder: Path) -> RunMeta:
    return RunMeta.model_validate(json.loads((folder / "meta.json").read_text(encoding="utf-8")))


def list_runs(runs_dir: Path | None = None) -> list[RunMeta]:
    """All saved runs, newest first. Corrupt or incomplete entries are skipped."""
    base = Path(runs_dir or RUNS_DIR)
    if not base.is_dir():
        return []
    metas = []
    for folder in base.iterdir():
        if not folder.is_dir() or not _valid_id(folder.name):
            continue
        try:
            m = _read_meta(folder)
        except (OSError, ValueError):  # JSON and validation errors are ValueErrors
            continue
        if m.run_id == folder.name:
            metas.append(m)
    return sorted(metas, key=lambda m: (m.created_at, m.run_id), reverse=True)


def load_run(run_id: str, runs_dir: Path | None = None) -> tuple[ScoutInput, CrewResult, RunMeta]:
    """Load a saved run. Raises FileNotFoundError for unknown/invalid ids, ValueError if corrupt."""
    folder = _run_path(run_id, runs_dir)
    if folder is None or not (folder / "meta.json").is_file():
        raise FileNotFoundError(f"Run not found: {run_id!r}")
    try:
        meta = _read_meta(folder)
        report = (folder / "report.md").read_text(encoding="utf-8")
        deck_file = folder / "pitch_deck.md"
        deck = deck_file.read_text(encoding="utf-8") if deck_file.is_file() else None
        inputs = ScoutInput(
            business_idea=meta.business_idea, city=meta.city,
            target_customer=meta.target_customer, known_competitors=meta.known_competitors)
    except OSError as e:
        raise ValueError(f"Run {run_id} is corrupt: {e}") from e
    result = CrewResult(report_markdown=report, pitch_deck_markdown=deck,
                        report_path=str(folder / "report.md"), warnings=meta.warnings)
    return inputs, result, meta


def delete_run(run_id: str, runs_dir: Path | None = None) -> bool:
    """Delete a saved run folder. Returns False if the id is invalid or the run does not exist."""
    folder = _run_path(run_id, runs_dir)
    if folder is None or not folder.is_dir():
        return False
    shutil.rmtree(folder)
    return True
