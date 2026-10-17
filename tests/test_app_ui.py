"""AppTest-based UI tests with a stubbed crew. Fakes for the logic layer are used only if the real modules are absent."""
import sys
import threading
import time
import types
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

HERE = Path(__file__).resolve().parent.parent
APP = str(HERE / "app.py")
sys.path.insert(0, str(HERE))

import ui_helpers as uh  # noqa: E402
from marketpulse.schemas import CrewResult, ScoutInput  # noqa: E402

REPORT = """# Report
## Key Competitors
| Competitor | Price | Strength | Weakness |
|---|---|---|---|
| A | $10 | fast | slow |
| B | $20 | cheap | rude |
## What Customers Complain About
- Long waits
## Sources
- https://example.com/a
"""


class FakeRun:
    def __init__(self, run_id, inputs, result, elapsed):
        self.run_id, self.business_idea, self.city = run_id, inputs.business_idea, inputs.city
        self.target_customer, self.known_competitors = inputs.target_customer, inputs.known_competitors
        self.hierarchical = self.pitch_deck = False
        self.warnings, self.elapsed_seconds, self.created_at = result.warnings, elapsed, "2026-01-01T10:00:00"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("SERPER_API_KEY", "x")
    store = {}
    if "history" not in sys.modules or not hasattr(sys.modules["history"], "save_run"):
        try:
            import history  # noqa: F401
        except ImportError:
            h = types.ModuleType("history")
            h.save_run = lambda i, r, hi, pd_, el: store.setdefault(f"r{len(store)}", (i, r, FakeRun(f"r{len(store)}", i, r, el))) and f"r{len(store) - 1}"
            h.list_runs = lambda: [v[2] for v in reversed(list(store.values()))]
            h.load_run = lambda rid: store[rid]
            h.delete_run = lambda rid: bool(store.pop(rid, None))
            monkeypatch.setitem(sys.modules, "history", h)
    try:
        import report_parse  # noqa: F401
    except ImportError:
        rpm = types.ModuleType("report_parse")
        rpm.parse_sections = lambda md: {"What Customers Complain About": "- Long waits"}
        rpm.parse_competitors = lambda md: pd.DataFrame({"Competitor": ["A", "B"], "Price": ["$10", "$20"], "Price Value": [10, 20]})
        rpm.price_chart_data = lambda df: df.set_index("Competitor")[["Price Value"]]
        rpm.sources_with_titles = lambda md: [("Example A", "https://example.com/a")]
        monkeypatch.setitem(sys.modules, "report_parse", rpm)
    if not hasattr(uh, "CancelToken"):
        class Tok:
            is_cancelled = False

            def cancel(self):
                self.is_cancelled = True
        monkeypatch.setattr(uh, "CancelToken", Tok, raising=False)
    if "cancel_token" not in uh.start_crew_worker.__code__.co_varnames:
        orig = uh.start_crew_worker
        monkeypatch.setattr(uh, "start_crew_worker", lambda *a, cancel_token=None, **k: orig(*a, **k))
    yield


def _stub(monkeypatch, behaviour="ok", gate=None):
    def fake(inputs, hierarchical=False, pitch_deck=False, step_callback=None, task_callback=None, **kw):
        if gate:
            gate.wait(5)
        if behaviour == "fail":
            raise RuntimeError("429 rate limit")
        if step_callback:
            step_callback(types.SimpleNamespace(thought="searching"), "Market Researcher")
        if task_callback:
            task_callback(types.SimpleNamespace(raw="done", agent="Market Researcher"))
        return CrewResult(report_markdown=REPORT, pitch_deck_markdown="# Deck" if pitch_deck else None,
                          report_path="r.md", warnings=["Missing section: X"])
    import marketpulse.crew as crew
    monkeypatch.setattr(crew, "run_crew", fake)


def _app():
    at = AppTest.from_file(APP, default_timeout=20)
    at.run()
    assert not at.exception
    return at


def _fill(at, idea="Pet spa", city="Austin", target="dog owners"):
    at.text_area(key="f_idea").set_value(idea)
    at.text_input(key="f_city").set_value(city)
    at.text_input(key="f_target").set_value(target)


def _settle(at, until, tries=60):
    for _ in range(tries):
        time.sleep(0.1)
        at.run()
        assert not at.exception
        if until(at):
            return
    raise AssertionError("did not settle")


def test_idle_state():
    at = _app()
    assert any("Run research" in b.label for b in at.button)
    assert not at.exception


def test_validation_inline():
    at = _app()
    at.text_input(key="f_city").set_value("Austin")
    [b for b in at.button if b.label == "Run research"][0].click()
    at.run()
    assert at.error and "required" in at.error[0].value


def test_run_to_done(monkeypatch):
    _stub(monkeypatch)
    at = _app()
    _fill(at)
    [b for b in at.button if b.label == "Run research"][0].click()
    at.run()
    assert not at.exception
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))
    assert any("Report quality checks" in e.label for e in at.expander)
    at = _reset_check(at)


def _reset_check(at):
    [b for b in at.button if b.label == "New research"][0].click()
    at.run()
    assert not at.exception and at.text_area(key="f_idea").value == "Pet spa"
    return at


def test_error_and_retry(monkeypatch):
    _stub(monkeypatch, "fail")
    at = _app()
    _fill(at)
    [b for b in at.button if b.label == "Run research"][0].click()
    at.run()
    _settle(at, lambda a: any(b.label == "Retry" for b in a.button))
    _stub(monkeypatch, "ok")
    [b for b in at.button if b.label == "Retry"][0].click()
    at.run()
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))


def _run_click(at):
    [b for b in at.button if b.label == "Run research"][0].click()
    at.run()
    assert not at.exception


def _html(at):
    return " ".join(str(e.value) for e in at.get("html"))


def test_cancel_keeps_inputs(monkeypatch):
    gate = threading.Event()
    _stub(monkeypatch, gate=gate)
    at = _app()
    _fill(at, idea="Keep me")
    _run_click(at)
    cancel = [b for b in at.button if b.label == "Cancel"]
    assert "mp-pipe" in _html(at)
    assert cancel and not at.exception
    cancel[0].click()
    at.run()
    gate.set()
    assert not at.exception
    assert at.text_area(key="f_idea").value == "Keep me"
    assert any("cancelled" in i.value for i in at.info)
    assert "job" not in at.session_state


def test_first_render_after_run_is_running_and_import_is_off_main_thread(monkeypatch):
    """The click must show the running screen at once; the heavy crew import happens in the worker thread."""
    imported_in = []
    release = threading.Event()
    fake_mod = types.ModuleType("marketpulse.crew")

    def run_crew(inputs, **kw):
        release.wait(5)
        return CrewResult(report_markdown=REPORT, report_path="r.md")

    def __getattr__(name):  # PEP 562: runs when `from marketpulse.crew import run_crew` resolves the name
        if name == "run_crew":
            imported_in.append(threading.current_thread().name)
            time.sleep(0.3)  # slow import
            return run_crew
        raise AttributeError(name)
    fake_mod.__getattr__ = __getattr__
    import marketpulse
    monkeypatch.setitem(sys.modules, "marketpulse.crew", fake_mod)
    monkeypatch.setattr(marketpulse, "crew", fake_mod, raising=False)

    at = _app()
    _fill(at)
    t0 = time.time()
    _run_click(at)
    assert time.time() - t0 < 0.25, "the click rerun must not wait for the slow import"
    assert imported_in == [] or imported_in == ["mp-crew-worker"]
    assert "mp-live" in _html(at) and "Getting the research team ready" in _html(at)
    assert any(b.label == "Cancel" for b in at.button)
    assert not [b for b in at.button if b.label == "Run research"], "the form must be gone"
    assert at.session_state["job"]["crew_ready"] is False
    time.sleep(0.6)
    assert imported_in == ["mp-crew-worker"]
    release.set()
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))


def test_import_error_surfaces_as_error_event(monkeypatch):
    fake_mod = types.ModuleType("marketpulse.crew")

    def __getattr__(name):
        raise ImportError("No module named 'crewai' (timeout)")
    fake_mod.__getattr__ = __getattr__
    import marketpulse
    monkeypatch.setitem(sys.modules, "marketpulse.crew", fake_mod)
    monkeypatch.setattr(marketpulse, "crew", fake_mod, raising=False)
    at = _app()
    _fill(at)
    _run_click(at)
    _settle(at, lambda a: any(b.label == "Retry" for b in a.button))
    assert "did not finish" in _html(at)


def test_running_screen_shows_stage_heartbeat_and_tool_activity(monkeypatch):
    gate = threading.Event()

    def fake(inputs, step_callback=None, task_callback=None, **kw):
        step_callback(types.SimpleNamespace(tool="Search the internet with Serper",
                                            tool_input={"search_query": "millet box Coimbatore"}),
                      "Market Researcher")
        gate.wait(5)
        return CrewResult(report_markdown=REPORT, report_path="r.md")
    import marketpulse.crew as crew
    monkeypatch.setattr(crew, "run_crew", fake)
    at = _app()
    _fill(at)
    _run_click(at)
    _settle(at, lambda a: "Searching" in _html(a))
    h = _html(at)
    assert "Market Researcher" in h and "searching the web" in h
    assert "Searching</span> millet box Coimbatore" in h
    assert "Last activity" in h and "Elapsed" in h and "mp-track" in h
    assert all(b.disabled for b in at.sidebar.button if b.key and b.key.startswith("open_"))
    gate.set()
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))


def test_example_card_fills_form():
    at = _app()
    at.button(key="ex_1").click()
    at.run()
    assert not at.exception
    assert at.text_input(key="f_city").value == uh.EXAMPLES[1]["city"]


def test_results_kpis_show_currency_and_unit(monkeypatch):
    _stub(monkeypatch)
    at = _app()
    _fill(at)
    _run_click(at)
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))
    h = _html(at)
    assert "mp-kpi" in h and "Average price" in h and "$15" in h


def test_history_open_and_delete(monkeypatch):
    _stub(monkeypatch)
    at = _app()
    _fill(at)
    [b for b in at.button if b.label == "Run research"][0].click()
    at.run()
    _settle(at, lambda a: any(b.label == "New research" for b in a.button))
    _reset_check(at)
    opens = [b for b in at.sidebar.button if b.key and b.key.startswith("open_")]
    assert opens
    opens[0].click()
    at.run()
    assert not at.exception
    assert any(b.label == "New research" for b in at.button)


def test_tool_use_is_described_in_plain_words():
    ns = types.SimpleNamespace
    ev = uh.format_step_event(ns(tool="Search the internet with Serper",
                                 tool_input='{"search_query": "millet box Coimbatore"}'), "Market Researcher")
    assert ev.text == "Searching: millet box Coimbatore"
    ev = uh.format_step_event(ns(tool="Read website content", tool_input={"website_url": "https://www.example.com/a"}))
    assert ev.text == "Reading: example.com"
    assert uh.format_step_event(ns(tool="Calculator", tool_input="2+2")).text == "Using Calculator: 2+2"
    assert uh.format_step_event(ns(thought="Comparing prices")).text == "Comparing prices"


def test_price_units_and_stage_headline():
    assert uh.price_units(["Rs 180 per meal", "Rs 150 per meal", "Rs 90"]) == ("Rs", "meal")
    assert uh.price_units(["$10", "$5/month"]) == ("$", "month")
    assert uh.price_units(["free", ""]) == ("", "")
    assert "searching the web" in uh.stage_headline("Market Researcher")
    assert uh.stage_headline("Report Writer", starting=True) == "Getting the research team ready"
    assert uh.ago_label(0) == "just now" and uh.ago_label(75) == "1m 15s ago"
