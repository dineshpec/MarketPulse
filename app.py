"""MarketPulse Streamlit app. Run: streamlit run app.py"""
from __future__ import annotations

import queue
import sys
import time
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
for _p in (str(_HERE), str(_HERE.parent)):  # flat helpers + `marketpulse` package
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ui_helpers as uh  # noqa: E402
import ui_style as sty  # noqa: E402
from report_export import extract_sources, markdown_to_pdf  # noqa: E402

try:  # logic layer: degrade gracefully if a module is unavailable
    import history
except ImportError:  # history uses package-relative imports: load it as marketpulse.history
    try:
        from marketpulse import history
    except ImportError:  # pragma: no cover
        history = None
try:
    import report_parse as rp
except ImportError:  # pragma: no cover
    rp = None

load_dotenv(_HERE / ".env")
load_dotenv()

st.set_page_config(page_title="MarketPulse", page_icon=":material/radar:", layout="wide",
                   initial_sidebar_state="auto")
ss = st.session_state
FIELDS = {"f_idea": "business_idea", "f_city": "city", "f_target": "target_customer", "f_known": "known_competitors"}
FALLBACK_EXAMPLES = [{"label": "Cloud kitchen", "business_idea": "A cloud kitchen selling healthy South Indian meal boxes",
                      "city": "Bengaluru", "target_customer": "Working professionals aged 25-40",
                      "known_competitors": ""}]
CANCEL_NOTICE = "Research cancelled. Your inputs are kept below."


# ---------------------------------------------------------------- helpers
def _examples() -> list[dict]:
    return getattr(uh, "EXAMPLES", None) or FALLBACK_EXAMPLES


def _title(inputs) -> str:
    fn = getattr(uh, "idea_title", None)
    return fn(inputs) if fn else (getattr(inputs, "business_idea", "") or "Untitled")[:60]


def _headline(inputs) -> str:
    return " ".join((getattr(inputs, "business_idea", "") or "Untitled").split())


def _elapsed(seconds) -> str:
    fn = getattr(uh, "elapsed_label", None)
    if fn:
        return fn(seconds)
    s = int(seconds or 0)
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def _rel_date(value) -> str:
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        secs = (datetime.now(dt.tzinfo) - dt).total_seconds()
    except (ValueError, TypeError):
        return ""
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    if secs < 7 * 86400:
        return f"{int(secs // 86400)} d ago"
    return dt.strftime("%d %b %Y")


def _new_token():
    cls = getattr(uh, "CancelToken", None)
    if cls:
        return cls()

    class _Tok:
        is_cancelled = False

        def cancel(self):
            self.is_cancelled = True
    return _Tok()


def _reset() -> None:
    for k in ("job", "result", "error", "notice", "run_id", "elapsed", "inputs_used"):
        ss.pop(k, None)


def _draft_to_widgets() -> None:
    d = ss.get("draft", {})
    for k, attr in FIELDS.items():
        if k not in ss:
            ss[k] = d.get(attr, "")


def _pick_example(idx: int) -> None:
    exs = _examples()
    if 0 <= idx < len(exs):
        for k, attr in FIELDS.items():
            ss[k] = exs[idx].get(attr, "")


# ---------------------------------------------------------------- job control
def _lazy_runner(job: dict):
    """run_fn for the worker thread: the heavy crewai import happens HERE (off the UI thread)."""
    def run(inputs, **kw):
        from marketpulse.crew import run_crew  # lazy: keeps the UI importable without LLM deps
        job["crew_ready"] = True
        return run_crew(inputs, **kw)
    return run


def start_job(inputs, hierarchical: bool, pitch_deck: bool) -> None:
    """Register the job as 'starting' and launch the worker thread. Returns immediately (no heavy import);
    the caller st.rerun()s so the running screen replaces the form on the very next render."""
    _reset()
    ss["draft"] = inputs.model_dump()
    ss["last_args"] = (inputs, hierarchical, pitch_deck)
    now = time.time()
    job = dict(q=queue.Queue(), token=_new_token(), inputs=inputs, hierarchical=hierarchical, pitch_deck=pitch_deck,
               started=now, last_event=now, events=[], done_tasks=0, last_role=None, outcome=None, payload=None,
               crew_ready=False)
    try:
        uh.start_crew_worker(_lazy_runner(job), inputs, job["q"], hierarchical=hierarchical, pitch_deck=pitch_deck,
                             cancel_token=job["token"])
    except Exception as e:  # noqa: BLE001
        ss["error"] = uh.friendly_error(e)
        return
    ss["job"] = job


def _drain(job: dict) -> None:
    while job["outcome"] is None:
        try:
            ev = job["q"].get_nowait()
        except queue.Empty:
            return
        job["last_event"] = time.time()
        job["crew_ready"] = True
        if ev.kind == "step":
            if ev.agent and ev.agent not in ("Agent", uh.MANAGER_LABEL):
                job["last_role"] = ev.agent
            job["events"].append(("step", ev.agent, ev.text))
        elif ev.kind == "task":
            job["done_tasks"] += 1
            job["events"].append(("task", ev.agent, ev.text))
        elif ev.kind in ("done", "error", "cancelled"):
            job["outcome"] = ev.kind
            job["payload"] = ev.payload if ev.kind == "done" else ev.text
            job["elapsed"] = time.time() - job["started"]


def _finalize(job: dict) -> None:
    ss.pop("job", None)
    if job["outcome"] == "done":
        res = job["payload"]
        ss["result"], ss["inputs_used"], ss["elapsed"] = res, job["inputs"], job["elapsed"]
        if history:
            try:
                ss["run_id"] = history.save_run(job["inputs"], res, job["hierarchical"], job["pitch_deck"],
                                                job["elapsed"])
            except Exception:  # noqa: BLE001 - history is best-effort
                ss["notice"] = "The report is ready, but it could not be saved to history."
    elif job["outcome"] == "cancelled":
        ss["notice"] = CANCEL_NOTICE
    else:
        ss["error"] = job["payload"] or "The research run failed."


def open_run(run_id: str) -> None:
    try:
        inputs, res, meta = history.load_run(run_id)
    except Exception as e:  # noqa: BLE001
        ss["error"] = f"Could not open that run: {e}"
        return
    _reset()
    ss.update(result=res, inputs_used=inputs, run_id=run_id, elapsed=getattr(meta, "elapsed_seconds", None),
              draft=inputs.model_dump())
    for k in FIELDS:
        ss.pop(k, None)


# ---------------------------------------------------------------- views
def render_header(missing: list[str]) -> None:
    st.html(f"<style>{sty.CSS}</style>")
    st.html(sty.header_html(missing))
    if "job" not in ss and not ss.get("result") and not ss.get("error"):
        st.html(sty.hero_html())


def render_sidebar(missing: list[str]) -> None:
    busy = "job" in ss
    with st.sidebar:
        st.markdown("#### :material/history: Run history")
        runs = []
        if history:
            try:
                runs = history.list_runs()
            except Exception:  # noqa: BLE001
                runs = []
        if busy:
            st.caption("History is locked while research is running.")
        if not runs:
            st.caption("Past research runs will appear here.")
        for r in runs[:30]:
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            active = ss.get("run_id") == r.run_id
            label = f"{(r.business_idea or 'Untitled')[:48]}  \n:gray[{r.city} · {_rel_date(r.created_at)}]"
            if c1.button(label, key=f"open_{r.run_id}", type="primary" if active else "tertiary",
                         disabled=busy, width="stretch", help="Open this report"):
                open_run(r.run_id)
                st.rerun()
            with c2.popover("", icon=":material/delete:", disabled=busy, help="Delete this run"):
                st.write("Delete this run permanently?")
                if st.button("Delete", key=f"del_{r.run_id}", type="primary", icon=":material/delete:"):
                    history.delete_run(r.run_id)
                    if ss.get("run_id") == r.run_id:
                        _reset()
                    st.rerun()
        st.divider()
        with st.expander("Settings", icon=":material/tune:"):
            st.toggle("Hierarchical process", key="opt_hier", disabled=busy,
                      help="A manager agent delegates and reviews work. Slower and uses more tokens.")
            st.toggle("Pitch deck agent", key="opt_deck", disabled=busy,
                      help="Adds a Pitch Deck Designer step before the report is written.")
        with st.expander("API keys", icon=":material/key:", expanded=bool(missing)):
            for k, name in uh.REQUIRED_KEYS.items():
                ok = k not in missing
                st.markdown(f"{':material/check_circle:' if ok else ':material/error:'} {name}"
                            f"{'' if ok else ' (missing)'}")
            if missing:
                st.caption("Copy `.env.example` to `.env`, fill in the keys, and restart the app.")


def render_form(missing: list[str]) -> None:
    notice = ss.pop("notice", None)
    if notice:
        st.info(notice, icon=":material/info:")
    err = ss.get("error")
    if err:
        st.html(sty.card_html("The research run did not finish", err, error=True))
        c1, c2, _ = st.columns([1, 1, 3])
        if c1.button("Retry", icon=":material/refresh:", disabled=bool(missing) or "last_args" not in ss):
            start_job(*ss["last_args"])
            st.rerun()
        if c2.button("Edit inputs", icon=":material/edit:"):
            ss.pop("error", None)
            st.rerun()
        return
    _draft_to_widgets()
    with st.container(border=True, key="mp_form"):
        st.html('<div class="mp-h">What do you want to launch?</div>'
                '<p class="mp-lead">Tell us about your idea, or start from an example.</p>')
        exs = _examples()
        cols = st.columns(len(exs))
        for i, (col, ex) in enumerate(zip(cols, exs)):
            name, _, where = ex["label"].partition(",")
            col.button(f"**{name}**\n\n{where.strip() or ex.get('city', '')}",
                       key=f"ex_{i}", on_click=_pick_example, args=(i,), width="stretch")
        with st.form("scout_form", border=False):
            st.text_area("Business idea", key="f_idea", height=80,
                         placeholder="A cloud kitchen selling healthy South Indian meal boxes")
            c1, c2 = st.columns(2)
            c1.text_input("City", key="f_city", placeholder="Bengaluru")
            c2.text_input("Target customer", key="f_target", placeholder="Working professionals aged 25-40")
            st.text_area("Known competitors (optional)", key="f_known", height=70,
                         placeholder="One per line or comma-separated")
            if missing:
                st.caption(":material/error: Add the missing API keys (see sidebar) to enable research.")
            submitted = st.form_submit_button("Run research", type="primary", icon=":material/play_arrow:",
                                              disabled=bool(missing), key="run_btn", width="stretch")
    if submitted:
        vals = {attr: (ss.get(k) or "") for k, attr in FIELDS.items()}
        ss["draft"] = vals
        errs = uh.validate_inputs(vals["business_idea"], vals["city"], vals["target_customer"],
                                  vals["known_competitors"])
        if errs:
            for e in errs:
                st.error(e, icon=":material/error:")
        else:
            from marketpulse.schemas import ScoutInput  # light (pydantic only)
            inputs = ScoutInput(**{k: v.strip() for k, v in vals.items()})
            start_job(inputs, bool(ss.get("opt_hier")), bool(ss.get("opt_deck")))
            st.rerun()  # next render shows the running screen at once; the heavy import runs in the worker
    st.html(sty.how_it_works_html())


@st.fragment(run_every=1)
def running_panel() -> None:
    job = ss.get("job")
    if not job:
        return
    _drain(job)
    if job["outcome"]:
        _finalize(job)
        st.rerun()
        return
    now = time.time()
    agents = uh.agent_sequence(job["pitch_deck"])
    done = min(job["done_tasks"], len(agents))
    active = min(done, len(agents) - 1)
    role = job["last_role"]
    if job["hierarchical"] and role in agents and agents.index(role) >= done:
        active = agents.index(role)
    starting = not job["crew_ready"]
    if job["hierarchical"] and not role:
        agent = uh.MANAGER_LABEL
    else:
        agent = agents[active]
    idle = now - job["last_event"]
    with st.container(border=True, key="mp_live"):
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        with c1:
            st.html(sty.run_head_html(_headline(job["inputs"]), escape(job["inputs"].city)
                                      + (" &middot; manager decides the order" if job["hierarchical"] else "")))
        if c2.button("Cancel", icon=":material/close:", key="cancel_run", width="stretch",
                     help="Stop this research run. Your inputs are kept."):
            job["token"].cancel()
            ss.pop("job", None)
            ss["notice"] = CANCEL_NOTICE
            st.rerun()
        st.html(sty.live_indicator_html())  # static markup: identical every tick, so the animation never restarts
        st.html(sty.now_html(agent, uh.stage_headline(agent, starting), active + 1, len(agents),
                             _elapsed(now - job["started"]), "waiting for first update" if not job["events"]
                             else uh.ago_label(idle), quiet=idle > 40 and not starting, starting=starting))
        st.html(sty.tips_html(uh.TIPS))  # static, pure-CSS rotation
        st.html(sty.stepper_html(agents, done, None if starting else active))
        events = job["events"]
        st.html('<div class="mp-sec">Live activity</div>')
        st.html(sty.feed_html(events[-8:][::-1]))
        if len(events) > 8:
            with st.expander(f"Earlier activity ({len(events) - 8})"):
                st.html(sty.feed_html(events[:-8][::-1]))


def render_running() -> None:
    job = ss["job"]
    if not job.get("scrolled"):  # the form was long (esp. on phones): start the running screen at the top
        job["scrolled"] = True
        st.html("<script>(document.querySelector('[data-testid=\"stMain\"]')||document.scrollingElement)"
                ".scrollTo({top:0});</script>", unsafe_allow_javascript=True)
    running_panel()


def _kpis(comps: pd.DataFrame, sources: list) -> list[tuple]:
    avg, cur, unit = "n/a", "", ""
    if comps is not None and "Price Value" in comps:
        vals = pd.to_numeric(comps["Price Value"], errors="coerce").dropna()
        if len(vals):
            cur, unit = uh.price_units(comps["Price"].tolist() if "Price" in comps else [])
            avg = f"{cur}{' ' if cur[-1:].isalpha() else ''}{vals.mean():,.0f}"
    el = ss.get("elapsed")
    return [("Competitors found", str(len(comps)) if comps is not None else "0", "storefront", ""),
            ("Average price", avg, "payments", f"per {unit}" if unit and avg != "n/a" else ""),
            ("Sources cited", str(len(sources)), "link", ""),
            ("Run time", _elapsed(el) if el is not None else "n/a", "timer", "")]


def _price_chart(chart: pd.DataFrame, axis_title: str) -> None:
    """Horizontal bars sorted by price, full competitor names, clean axis title, value labels."""
    import altair as alt
    base = alt.Chart(chart).encode(
        y=alt.Y("Competitor:N", sort=list(chart["Competitor"]), title=None,
                axis=alt.Axis(labelLimit=260, labelFontSize=12, ticks=False, domain=False)),
        x=alt.X("Price Value:Q", title=axis_title, axis=alt.Axis(tickCount=5, format=",.0f", grid=True)),
        tooltip=[alt.Tooltip("Competitor:N"), alt.Tooltip("Price Value:Q", title="Price", format=",.0f")])
    bars = base.mark_bar(color="#0d6b63", cornerRadiusEnd=5, size=24)
    labels = base.mark_text(align="right", dx=-7, color="#ffffff", fontWeight="bold").encode(text=alt.Text("Price Value:Q", format=",.0f"))
    st.altair_chart((bars + labels).properties(height=44 * len(chart) + 30), width="stretch")


def render_results(res) -> None:
    inputs = ss.get("inputs_used")
    report_md = rp.strip_code_fence(getattr(res, "report_markdown", "") or "") if rp else (getattr(res, "report_markdown", "") or "")
    deck_md = getattr(res, "pitch_deck_markdown", None)
    both = report_md + "\n" + (deck_md or "")
    comps = rp.parse_competitors(report_md) if rp else pd.DataFrame()
    sections = rp.parse_sections(report_md) if rp else {}
    sources = rp.sources_with_titles(both) if rp else [(u, u) for u in extract_sources(both)]

    top, btn = st.columns([4, 1], vertical_alignment="center")
    if inputs is not None:
        top.html(sty.result_head_html(_headline(inputs), f"{inputs.city} · {inputs.target_customer}"))
    if btn.button("New research", icon=":material/add:", type="primary", width="stretch"):
        _reset()
        st.rerun()
    notice = ss.pop("notice", None)
    if notice:
        st.info(notice, icon=":material/info:")
    st.html(sty.kpi_html(_kpis(comps, sources)))

    names = ["Report", "Competitors", "Customer voice"] + (["Pitch deck"] if deck_md else []) + ["Sources"]
    tabs = dict(zip(names, st.tabs(names)))
    with tabs["Report"]:
        st.markdown(report_md)
    with tabs["Competitors"]:
        if comps is not None and len(comps):
            cfg = {"Price Value": st.column_config.NumberColumn("Price (numeric)", format="%.0f")}
            st.dataframe(comps, hide_index=True, width="stretch",
                         column_config={k: v for k, v in cfg.items() if k in comps.columns})
            chart = rp.price_chart_data(comps) if rp else None
            if chart is not None and len(chart):
                cur, unit = uh.price_units(comps["Price"].tolist() if "Price" in comps else [])
                axis = "Price" + (f" ({cur}{' per ' + unit if unit else ''})" if cur or unit else "")
                st.html('<div class="mp-sec">Price comparison</div>')
                chart = chart.sort_values("Price Value", ascending=False).reset_index(drop=True)
                _price_chart(chart, axis)
        else:
            st.caption("No competitor table could be read from this report. See the Report tab.")
    with tabs["Customer voice"]:
        key = next((k for k in sections if "complain" in k.lower() or "customer" in k.lower()), None)
        if key:
            st.markdown(sections[key])
        else:
            st.caption("No customer-complaints section was found in this report.")
    if deck_md:
        with tabs["Pitch deck"]:
            st.markdown(deck_md)
    with tabs["Sources"]:
        if sources:
            for label, url in sources:
                st.markdown(f"- [{label}]({url})" if label != url else f"- <{url}>")
        else:
            st.caption("No source links were found in the report.")

    warns = getattr(res, "warnings", None) or []
    title = f"Report quality checks ({len(warns)} flagged)" if warns else "Report quality checks (all passed)"
    with st.expander(title, icon=":material/fact_check:"):
        if warns:
            for w in warns:
                st.markdown(f"- {w}")
        else:
            st.caption("No issues detected by the automatic checks.")

    d1, d2, d3, _ = st.columns([1, 1, 1, 2])
    d1.download_button("Markdown", report_md, file_name="marketpulse_report.md", mime="text/markdown",
                       icon=":material/description:", width="stretch")
    d2.download_button("PDF", markdown_to_pdf(report_md), file_name="marketpulse_report.pdf",
                       mime="application/pdf", icon=":material/picture_as_pdf:", width="stretch")
    if deck_md:
        d3.download_button("Pitch deck", deck_md, file_name="marketpulse_pitch_deck.md", mime="text/markdown",
                           icon=":material/slideshow:", width="stretch")


# ---------------------------------------------------------------- main
def main() -> None:
    missing = uh.missing_keys()
    render_header(missing)
    render_sidebar(missing)
    if "job" in ss:
        render_running()
    elif ss.get("result") and not ss.get("error"):
        render_results(ss["result"])
    else:
        render_form(missing)


main()
