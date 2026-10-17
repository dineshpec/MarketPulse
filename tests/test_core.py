"""Offline tests: no network or real API keys needed."""
import pytest
from pydantic import ValidationError

from marketpulse.validate_report import validate_report


def _inputs(**kw):
    from marketpulse.schemas import ScoutInput

    base = dict(business_idea="premium pet grooming", city="Austin", target_customer="busy dog owners")
    base.update(kw)
    return ScoutInput(**base)


# ---------- schemas ----------
def test_scout_input_valid_defaults():
    assert _inputs().known_competitors == ""


@pytest.mark.parametrize("field", ["business_idea", "city", "target_customer"])
def test_scout_input_rejects_empty(field):
    with pytest.raises(ValidationError):
        _inputs(**{field: "   "})


# ---------- crew ----------
def test_build_crew_sequential(dummy_env):
    from crewai import Process
    from marketpulse.crew import build_crew

    c = build_crew(_inputs())
    assert len(c.agents) == 4 and len(c.tasks) == 4
    assert c.process == Process.sequential


def test_build_crew_pitch_deck(dummy_env):
    from marketpulse.crew import build_crew

    c = build_crew(_inputs(), pitch_deck=True)
    assert len(c.agents) == 5 and len(c.tasks) == 5


def test_build_crew_hierarchical(dummy_env):
    from crewai import Process
    from marketpulse.crew import build_crew

    c = build_crew(_inputs(), hierarchical=True)
    assert c.process == Process.hierarchical


# ---------- validate_report ----------
def test_good_report_passes(good_report):
    assert validate_report(good_report) == []


def test_empty_report():
    assert validate_report("") == ["Report is empty."]


def test_missing_sections_reported(good_report):
    bad = good_report.replace("## Market Gap", "## Something Else")
    assert any("Market Gap" in p for p in validate_report(bad))


def test_too_few_competitors(good_report):
    bad = "\n".join(l for l in good_report.splitlines() if "Bark & Bubbles |" not in l)
    assert any("at least 3" in p for p in validate_report(bad))


def test_competitor_without_price(good_report):
    bad = good_report.replace("$80 per groom", "unknown")
    assert any("Pawfect Spa" in p and "price" in p for p in validate_report(bad))


def test_sources_without_link(good_report):
    bad = good_report.split("## Sources")[0] + "## Sources\n- some website\n"
    assert any("Sources" in p for p in validate_report(bad))


# ---------- missing keys ----------
def test_missing_openai_key_raises(monkeypatch):
    from marketpulse.crew import build_crew

    monkeypatch.setattr("marketpulse.crew.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SERPER_API_KEY", "dummy")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_crew(_inputs())


def test_missing_serper_key_raises(monkeypatch):
    from marketpulse.crew import build_crew

    monkeypatch.setattr("marketpulse.crew.load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr("marketpulse.tools.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SERPER_API_KEY"):
        build_crew(_inputs())


def test_agent_roles(dummy_env):
    from marketpulse.crew import build_crew

    roles = [a.role for a in build_crew(_inputs(), pitch_deck=True).agents]
    for r in ["Market Researcher", "Review Analyst", "Strategy Analyst", "Report Writer", "Pitch Deck Designer"]:
        assert any(r in x for x in roles)


# ---------- validator: any price unit ----------
@pytest.mark.parametrize("price", ["Rs 120 per meal", "49/month", "12 EUR per class", "Free trial", "3.5 credits per kg"])
def test_validator_accepts_any_unit(good_report, price):
    assert validate_report(good_report.replace("$80 per groom", price)) == []


def test_validator_price_column_header_with_unit(good_report):
    md = good_report.replace("| Competitor | Price |", "| Competitor | Price (with unit) |")
    assert validate_report(md) == []
    assert any("no price" in p for p in validate_report(md.replace("$80 per groom", "n/a")))


def test_validator_ignores_digits_outside_price_column(good_report):
    md = good_report.replace("$80 per groom | Luxury feel", "tbd | Open 24 hours")
    assert any("Pawfect Spa" in p for p in validate_report(md))


# ---------- ui_helpers ----------
def test_format_step_event_uses_role():
    from types import SimpleNamespace
    from marketpulse.ui_helpers import format_step_event

    step = SimpleNamespace(tool="search", tool_input="pet grooming austin")
    assert format_step_event(step, "Market Researcher").agent == "Market Researcher"
    assert format_step_event(step).agent == "Agent"


def test_agent_sequence_pitch_deck_before_writer():
    from marketpulse.ui_helpers import agent_sequence, current_agent

    seq = agent_sequence(True)
    assert seq[-2:] == ["Pitch Deck Designer", "Report Writer"]
    assert [current_agent(i, True) for i in range(5)] == seq
    assert agent_sequence(False)[-1] == "Report Writer" and len(agent_sequence(False)) == 4


def test_current_agent_hierarchical_uses_last_role():
    from marketpulse.ui_helpers import current_agent

    assert current_agent(1, False, True, "Review Analyst").startswith("Review Analyst")
    assert "Manager delegating" in current_agent(0, False, True, None)
    assert "(2/4" in current_agent(2, False, True, None)


def test_hierarchical_task_event_not_manager():
    from types import SimpleNamespace
    from marketpulse.ui_helpers import format_task_event

    t = SimpleNamespace(raw="done", agent="Crew Manager")
    assert format_task_event(t, hierarchical=True).agent == "Task"
    assert format_task_event(t).agent == "Crew Manager"


def test_agents_get_own_step_callbacks(dummy_env):
    from types import SimpleNamespace
    from marketpulse.crew import build_crew

    seen = []
    c = build_crew(_inputs(), pitch_deck=True, step_callback=lambda s, role: seen.append(role))
    for a in c.agents:
        a.step_callback(SimpleNamespace(thought="x"))
    assert sorted(seen) == sorted(a.role for a in c.agents)


def test_pitch_deck_task_order_and_expected_output(dummy_env):
    from marketpulse.crew import build_crew

    c = build_crew(_inputs(), pitch_deck=True)
    assert [t.agent.role for t in c.tasks][-2:] == ["Pitch Deck Designer", "Report Writer"]
    assert "Price (with unit)" in c.tasks[0].expected_output
    assert all("Price/meal" not in t.description and "per unit/meal" not in t.description for t in c.tasks)


# ---------- warnings wiring ----------
def test_crew_result_warnings_default():
    from marketpulse.schemas import CrewResult

    r = CrewResult(report_markdown="x", report_path="p")
    assert r.warnings == []
    assert CrewResult(report_markdown="x", report_path="p", warnings=["a"]).warnings == ["a"]


def test_run_crew_populates_warnings(dummy_env, monkeypatch, tmp_path):
    from types import SimpleNamespace
    from marketpulse import crew as crew_mod

    class FakeCrew:
        def __init__(self):
            self.tasks = [SimpleNamespace(agent=SimpleNamespace(role="Report Writer"),
                                          output=SimpleNamespace(raw="# bad report"))]

        def kickoff(self, inputs):
            return SimpleNamespace(tasks_output=[SimpleNamespace(raw="# bad report")], raw="# bad report")

    monkeypatch.setattr(crew_mod, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(crew_mod, "build_crew", lambda *a, **k: FakeCrew())
    res = crew_mod.run_crew(_inputs())
    assert res.report_markdown == "# bad report"
    assert any("Missing section" in w for w in res.warnings)


# ---------- cancellation / examples / labels ----------
def _drain(q):
    out = []
    while not q.empty():
        out.append(q.get())
    return out


def test_cancel_token_basics():
    from marketpulse.ui_helpers import CancelToken, CrewCancelled

    t = CancelToken()
    t.check()  # no-op while not cancelled
    assert not t.is_cancelled
    t.cancel()
    assert t.is_cancelled
    with pytest.raises(CrewCancelled):
        t.check()


def test_worker_emits_cancelled_not_error():
    import queue

    from marketpulse.ui_helpers import CancelToken, start_crew_worker

    token = CancelToken()
    q = queue.Queue()

    def fake_run(inputs, hierarchical, pitch_deck, step_callback, task_callback, cancel_token=None):
        step_callback("thinking", "Market Researcher")  # passes: not cancelled yet
        token.cancel()
        step_callback("more thinking", "Market Researcher")  # raises CrewCancelled
        raise AssertionError("should have been aborted")

    start_crew_worker(fake_run, _inputs(), q, cancel_token=token).join(5)
    kinds = [e.kind for e in _drain(q)]
    assert kinds == ["step", "cancelled"]


def test_worker_cancelled_even_if_wrapped_error():
    import queue

    from marketpulse.ui_helpers import CancelToken, start_crew_worker

    token = CancelToken()
    q = queue.Queue()

    def fake_run(inputs, **kw):
        token.cancel()
        raise RuntimeError("wrapped by crewai")

    start_crew_worker(fake_run, _inputs(), q, cancel_token=token).join(5)
    assert [e.kind for e in _drain(q)] == ["cancelled"]


def test_worker_backcompat_without_token():
    import queue

    from marketpulse.ui_helpers import start_crew_worker

    q = queue.Queue()

    def old_run(inputs, hierarchical, pitch_deck, step_callback, task_callback):  # no cancel_token param
        return "ok"

    start_crew_worker(old_run, _inputs(), q).join(5)
    evs = _drain(q)
    assert [e.kind for e in evs] == ["done"] and evs[0].payload == "ok"

    def bad_run(inputs, **kw):
        raise RuntimeError("boom")

    start_crew_worker(bad_run, _inputs(), q).join(5)
    assert [e.kind for e in _drain(q)] == ["error"]


def test_build_crew_guards_llm_and_callbacks(dummy_env):
    from marketpulse.crew import build_crew
    from marketpulse.ui_helpers import CancelToken, CrewCancelled

    token = CancelToken()
    seen = []
    c = build_crew(_inputs(), step_callback=lambda s, r=None: seen.append(r),
                   task_callback=lambda t: seen.append("task"), cancel_token=token)
    agent = c.agents[0]
    agent.step_callback("step")  # not cancelled: forwarded with the role
    c.task_callback("out")
    assert seen == ["Market Researcher", "task"]
    token.cancel()
    with pytest.raises(CrewCancelled):
        agent.step_callback("step")
    with pytest.raises(CrewCancelled):
        c.task_callback("out")
    with pytest.raises(CrewCancelled):
        agent.llm.call([{"role": "user", "content": "hi"}])  # guard fires before any network use


def test_run_crew_cancelled_before_kickoff(dummy_env):
    from marketpulse.crew import run_crew
    from marketpulse.ui_helpers import CancelToken, CrewCancelled

    token = CancelToken()
    token.cancel()
    with pytest.raises(CrewCancelled):
        run_crew(_inputs(), cancel_token=token)


def test_examples_valid():
    from marketpulse.schemas import ScoutInput
    from marketpulse.ui_helpers import EXAMPLES, validate_inputs

    assert len(EXAMPLES) >= 4
    keys = {"label", "business_idea", "city", "target_customer", "known_competitors"}
    for ex in EXAMPLES:
        assert set(ex) == keys
        ScoutInput(**{k: v for k, v in ex.items() if k != "label"})
        assert validate_inputs(ex["business_idea"], ex["city"], ex["target_customer"], ex["known_competitors"]) == []
    labels = " ".join(e["label"] for e in EXAMPLES)
    assert "Coimbatore" in labels and "Austin" in labels


def test_elapsed_label():
    from marketpulse.ui_helpers import elapsed_label

    assert elapsed_label(0) == "0s"
    assert elapsed_label(44.6) == "45s"
    assert elapsed_label(185) == "3m 05s"
    assert elapsed_label(3720) == "1h 02m"
    assert elapsed_label(None) == "0s"
    assert elapsed_label(-5) == "0s"


def test_idea_title():
    from marketpulse.ui_helpers import idea_title

    assert idea_title(_inputs()) == "premium pet grooming - Austin"
    long = idea_title(_inputs(business_idea="x" * 200))
    assert len(long) == 60 and long.endswith("...")
