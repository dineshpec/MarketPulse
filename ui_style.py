"""CSS and HTML snippets for the MarketPulse UI. Pure string builders (no Streamlit calls)."""
from __future__ import annotations

from html import escape

FONT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');"

CSS = FONT_IMPORT + r"""
html, body, [class*="st-"], .stApp { font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
/* the blanket font rule above must not clobber Streamlit's icon ligature font */
[data-testid="stIconMaterial"], [data-testid="stExpanderIcon"], span[translate="no"][aria-hidden="true"], .material-icons, .material-symbols-rounded, [class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons' !important; }
:root {
  --mp-accent:#0d6b63; --mp-accent-ink:#ffffff; --mp-accent-soft:rgba(13,107,99,.10);
  --mp-warm:#b45309; --mp-warm-soft:rgba(180,83,9,.10); --mp-bad:#b91c1c;
  --mp-line:rgba(22,33,43,.14); --mp-soft:rgba(22,33,43,.045); --mp-muted:#51606b;
  --mp-card:#ffffff; --mp-shadow:0 1px 2px rgba(22,33,43,.06), 0 8px 24px -12px rgba(22,33,43,.18);
  --mp-hero:linear-gradient(135deg, rgba(13,107,99,.10), rgba(180,83,9,.08));
}
@media (prefers-color-scheme: dark) { :root {
  --mp-accent:#2dd4bf; --mp-accent-ink:#06201d; --mp-accent-soft:rgba(45,212,191,.12);
  --mp-warm:#fbbf24; --mp-warm-soft:rgba(251,191,36,.12); --mp-bad:#f87171;
  --mp-line:rgba(232,238,240,.16); --mp-soft:rgba(232,238,240,.05); --mp-muted:#a7b6bd;
  --mp-card:#16262f; --mp-shadow:0 1px 2px rgba(0,0,0,.3), 0 10px 30px -14px rgba(0,0,0,.6);
  --mp-hero:linear-gradient(135deg, rgba(45,212,191,.12), rgba(251,191,36,.07));
} }
.block-container { max-width: 980px; padding-top: 2.2rem; padding-bottom: 4rem; }
@media (max-width: 640px) { .block-container { padding-top: 3.6rem; padding-left: 1rem; padding-right: 1rem; } }
.mp-ico { font-family:'Material Symbols Rounded' !important; font-weight:400; font-style:normal; line-height:1;
  letter-spacing:normal; text-transform:none; display:inline-block; white-space:nowrap; font-size:1.25rem;
  vertical-align:middle; font-feature-settings:'liga'; -webkit-font-feature-settings:'liga'; }

/* ---------- brand bar + hero ---------- */
.mp-bar-top { display:flex; align-items:center; justify-content:space-between; gap:.75rem; flex-wrap:wrap; margin-bottom:.9rem; }
.mp-logo { display:flex; align-items:center; gap:.55rem; font-weight:800; font-size:1.25rem; letter-spacing:-.02em; }
.mp-logo .mark { width:2rem; height:2rem; border-radius:.6rem; background:var(--mp-accent); color:var(--mp-accent-ink);
  display:grid; place-items:center; }
.mp-logo b { color:var(--mp-warm); font-weight:800; }
.mp-chips { display:flex; flex-wrap:wrap; gap:.4rem; }
.mp-chip { display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--mp-line);
  border-radius:999px; padding:.18rem .7rem; font-size:.8rem; font-weight:500; background:var(--mp-card); }
.mp-chip.ok::before { content:"\2713"; color:var(--mp-accent); font-weight:700; }
.mp-chip.bad::before { content:"!"; color:var(--mp-warm); font-weight:700; }
.mp-chip.bad { border-color: var(--mp-warm); }
.mp-hero { background:var(--mp-hero); border:1px solid var(--mp-line); border-radius:1.4rem; padding:2.2rem 2rem 2rem;
  margin:.4rem 0 1.4rem; text-align:center; }
.mp-hero .eyebrow { display:inline-block; font-size:.75rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase;
  color:var(--mp-accent); background:var(--mp-accent-soft); padding:.25rem .7rem; border-radius:999px; }
.mp-hero h1 { font-size:2.7rem; line-height:1.1; letter-spacing:-.035em; font-weight:800; margin:.9rem auto .7rem;
  max-width:18ch; padding:0; }
.mp-hero h1 em { font-style:normal; color:var(--mp-accent); }
.mp-hero p { color:var(--mp-muted); font-size:1.08rem; line-height:1.55; max-width:56ch; margin:0 auto; }
.mp-hero .facts { display:flex; flex-wrap:wrap; justify-content:center; gap:.5rem 1.4rem; margin-top:1.1rem;
  font-size:.88rem; font-weight:500; }
.mp-hero .facts span { display:inline-flex; align-items:center; gap:.35rem; }
.mp-hero .facts .mp-ico { color:var(--mp-accent); font-size:1.15rem; }
@media (max-width: 640px) { .mp-hero { padding:1.5rem 1.1rem; } .mp-hero h1 { font-size:1.9rem; } .mp-hero p { font-size:1rem; } }

/* ---------- form card + examples ---------- */
[class*="st-key-mp_form"], [class*="st-key-mp_live"] { background:var(--mp-card); border-radius:1.2rem !important;
  box-shadow:var(--mp-shadow); border-color:var(--mp-line) !important; padding:.4rem .6rem; }
.mp-h { font-size:1.25rem; font-weight:700; letter-spacing:-.015em; margin:.2rem 0 .1rem; }
.mp-lead { color:var(--mp-muted); font-size:.92rem; margin:0 0 .6rem; }
.mp-label { font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--mp-muted); margin:.2rem 0 .4rem; }
[class*="st-key-ex_"] button { width:100%; min-height:4.4rem; text-align:left; justify-content:flex-start; border-radius:.9rem;
  border:1px solid var(--mp-line); background:var(--mp-soft); padding:.6rem .8rem; transition:border-color .15s, transform .15s; }
[class*="st-key-ex_"] button:hover { border-color:var(--mp-accent); transform:translateY(-1px); }
[class*="st-key-ex_"] [data-testid="stMarkdownContainer"] { white-space:normal !important; overflow:visible !important; text-overflow:clip !important; display:block !important; width:100%; text-align:left !important; }
[class*="st-key-ex_"] button p { text-align:left; font-size:.86rem; line-height:1.3; margin:0; }
[class*="st-key-ex_"] button p strong { font-size:.95rem; }
[class*="st-key-ex_"] button p { display:block; }
[class*="st-key-ex_"] button p + p { color:var(--mp-muted); font-size:.8rem; margin-top:.1rem; }
[class*="st-key-run_btn"] button { min-height:3.2rem; font-weight:700; font-size:1.05rem; border-radius:.8rem; }
button:focus-visible, a:focus-visible, [role="tab"]:focus-visible { outline:3px solid var(--mp-warm) !important; outline-offset:2px; }
.mp-steps { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.8rem; margin-top:1.4rem; }
.mp-step { border:1px solid var(--mp-line); border-radius:1rem; padding:1rem; background:var(--mp-card); }
@media (max-width: 640px) {
  [data-testid="stHorizontalBlock"]:has([class*="st-key-ex_"]) { flex-wrap:wrap !important; gap:.5rem !important; }
  [data-testid="stHorizontalBlock"]:has([class*="st-key-ex_"]) > [data-testid="stColumn"] { flex:1 1 calc(50% - .5rem) !important; min-width:calc(50% - .5rem) !important; width:auto !important; }
  [class*="st-key-ex_"] button { min-height:3.6rem; padding:.5rem .6rem; }
}
.mp-step .ic { width:2.2rem; height:2.2rem; border-radius:.65rem; background:var(--mp-accent-soft); color:var(--mp-accent);
  display:grid; place-items:center; margin-bottom:.6rem; }
.mp-step .n { font-size:.7rem; font-weight:700; letter-spacing:.1em; color:var(--mp-muted); text-transform:uppercase; }
.mp-step .t { font-weight:700; margin:.1rem 0 .2rem; font-size:1.02rem; }
.mp-step .d { font-size:.86rem; color:var(--mp-muted); line-height:1.45; }
.mp-card { border:1px solid var(--mp-line); border-radius:1rem; padding:1.1rem 1.25rem; background:var(--mp-card); box-shadow:var(--mp-shadow); }
.mp-card.err { border-color:var(--mp-bad); border-left-width:5px; }
.mp-card h4 { margin:0 0 .3rem; display:flex; align-items:center; gap:.4rem; }
.mp-card.err h4 .mp-ico { color:var(--mp-bad); }

/* ---------- running screen ---------- */
.mp-run-head .eyebrow { font-size:.72rem; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:var(--mp-warm); }
.mp-run-head .ttl { font-size:1.3rem; font-weight:700; letter-spacing:-.02em; margin:.1rem 0; }
.mp-sub { color:var(--mp-muted); font-size:.9rem; }
.mp-sub b { color:inherit; font-variant-numeric:tabular-nums; }
.mp-live { display:flex; align-items:center; gap:.9rem; margin:.5rem 0 .2rem; }
.mp-spin { flex:none; width:1.7rem; height:1.7rem; border-radius:50%; border:3px solid var(--mp-line);
  border-top-color:var(--mp-accent); border-right-color:var(--mp-accent); animation:mp-rot .9s linear infinite; }
.mp-track { position:relative; flex:1; height:.45rem; border-radius:999px; background:var(--mp-line); overflow:hidden; }
.mp-track i { position:absolute; top:0; bottom:0; left:-40%; width:40%; border-radius:inherit;
  background:linear-gradient(90deg, transparent, var(--mp-accent), var(--mp-warm), transparent); animation:mp-slide 1.7s ease-in-out infinite; }
@keyframes mp-rot { to { transform:rotate(360deg); } }
@keyframes mp-slide { 0% { left:-40%; } 100% { left:100%; } }
.mp-now { font-size:1.2rem; font-weight:700; letter-spacing:-.015em; line-height:1.3; margin:.7rem 0 .25rem; }
.mp-now .who { color:var(--mp-accent); }
.mp-beat { display:flex; flex-wrap:wrap; gap:.3rem 1.2rem; font-size:.88rem; color:var(--mp-muted); }
.mp-beat span { display:inline-flex; align-items:center; gap:.3rem; }
.mp-beat b { color:var(--mp-accent); font-variant-numeric:tabular-nums; }
.mp-beat .dot { width:.55rem; height:.55rem; border-radius:50%; background:var(--mp-accent); }
.mp-beat .dot.slow { background:var(--mp-warm); }
.mp-tips { position:relative; height:2.6rem; margin:.5rem 0 .3rem; padding:.55rem .8rem; border-radius:.8rem; background:var(--mp-accent-soft);
  overflow:hidden; }
.mp-tips span { position:absolute; left:.8rem; right:.8rem; top:.62rem; opacity:0; font-size:.92rem; font-weight:500;
  animation:mp-tip 40s linear infinite; }
.mp-tips span:nth-child(1) { animation-delay:0s; } .mp-tips span:nth-child(2) { animation-delay:8s; }
.mp-tips span:nth-child(3) { animation-delay:16s; } .mp-tips span:nth-child(4) { animation-delay:24s; }
.mp-tips span:nth-child(5) { animation-delay:32s; }
@keyframes mp-tip { 0% { opacity:0; transform:translateY(6px); } 2% { opacity:1; transform:none; } 18% { opacity:1; transform:none; }
  20% { opacity:0; transform:translateY(-6px); } 100% { opacity:0; } }
@media (max-width: 640px) { .mp-tips { height:3.9rem; } }
.stHtml ol.mp-pipe, .stHtml ul.mp-feed { padding-left:0 !important; margin-left:0 !important; }
.mp-pipe { display:flex; margin:1rem 0 .4rem; padding:0; list-style:none; counter-reset:none; }
.mp-node { flex:1 1 0; position:relative; text-align:center; min-width:0; }
.mp-node + .mp-node::before { content:""; position:absolute; top:calc(1.1rem - 1px); left:-50%; width:100%; height:2px; background:var(--mp-line); }
.mp-node.done::before, .mp-node.active::before { background:var(--mp-accent); }
.mp-dot { position:relative; z-index:1; width:2.2rem; height:2.2rem; margin:0 auto .45rem; border-radius:50%; display:grid; place-items:center;
  font-weight:700; font-size:.88rem; border:2px solid var(--mp-line); background:var(--mp-card); color:var(--mp-muted); }
.mp-lbl { display:block; padding:0 .2rem; }
.mp-lbl .a { display:block; font-weight:600; font-size:.88rem; line-height:1.25; }
.mp-lbl .s { display:block; font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--mp-muted); margin-top:.15rem; }
.mp-node.done .mp-dot { background:var(--mp-accent); border-color:var(--mp-accent); color:var(--mp-accent-ink); }
.mp-node.done .s { color:var(--mp-accent); }
.mp-node.active .mp-dot { border-color:var(--mp-warm); color:var(--mp-warm); background:var(--mp-warm-soft); animation:mp-ring 2s ease-out infinite; }
.mp-node.active .s { color:var(--mp-warm); }
.mp-node.pending .a { color:var(--mp-muted); }
@keyframes mp-ring { 0% { box-shadow:0 0 0 0 var(--mp-warm-soft), 0 0 0 0 var(--mp-warm); } 70% { box-shadow:0 0 0 10px transparent; }
  100% { box-shadow:0 0 0 0 transparent; } }
@media (max-width: 640px) {
  .mp-pipe { flex-direction:column; gap:0; }
  .mp-node { display:flex; align-items:center; gap:.8rem; text-align:left; padding:.35rem 0; }
  .mp-dot { margin:0; flex:none; }
  .mp-node + .mp-node::before { top:-50%; left:1.1rem; width:2px; height:100%; }
}
@media (prefers-reduced-motion: reduce) {
  .mp-spin { animation-duration:3s; } .mp-track i { animation:none; left:0; width:100%; opacity:.45; }
  .mp-node.active .mp-dot { animation:none; } .mp-tips span { animation:none; } .mp-tips span:first-child { opacity:1; }
}
.mp-feedwrap h5, .mp-sec { font-size:.78rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--mp-muted); margin:.8rem 0 .3rem; }
.mp-feed { list-style:none; margin:0; padding:0; font-size:.9rem; }
.mp-feed li { display:flex; gap:.6rem; align-items:flex-start; padding:.5rem 0; border-bottom:1px solid var(--mp-line); }
.mp-feed li:last-child { border-bottom:none; }
.mp-feed .ic { flex:none; width:1.8rem; height:1.8rem; border-radius:.5rem; display:grid; place-items:center; background:var(--mp-soft); color:var(--mp-accent); }
.mp-feed .ic .mp-ico { font-size:1.1rem; }
.mp-feed li.task .ic { background:var(--mp-accent); color:var(--mp-accent-ink); }
.mp-feed .who { display:block; font-size:.75rem; font-weight:600; color:var(--mp-muted); }
.mp-feed .tx { overflow-wrap:anywhere; }
.mp-feed .k { font-weight:700; color:var(--mp-accent); }
.mp-skel { height:.7rem; border-radius:99px; margin:.55rem 0; background:linear-gradient(90deg, var(--mp-soft), var(--mp-line), var(--mp-soft));
  background-size:200% 100%; animation:mp-shim 1.8s linear infinite; }
@keyframes mp-shim { 0% { background-position:200% 0; } 100% { background-position:-200% 0; } }

/* ---------- results ---------- */
.mp-res-head .ttl { font-size:1.55rem; font-weight:800; letter-spacing:-.025em; line-height:1.2; margin:0; }
.mp-res-head .sub { color:var(--mp-muted); font-size:.95rem; margin-top:.2rem; }
.mp-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.8rem; margin:.8rem 0 1.2rem; }
.mp-kpi { display:flex; gap:.8rem; align-items:center; border:1px solid var(--mp-line); border-radius:1rem; padding:.85rem 1rem; background:var(--mp-card); box-shadow:var(--mp-shadow); }
.mp-kpi .ic { flex:none; width:2.5rem; height:2.5rem; border-radius:.75rem; display:grid; place-items:center; background:var(--mp-accent-soft); color:var(--mp-accent); }
.mp-kpi .v { font-size:1.55rem; font-weight:800; letter-spacing:-.03em; line-height:1.1; font-variant-numeric:tabular-nums; }
.mp-kpi .v small { font-size:.78rem; font-weight:600; color:var(--mp-muted); letter-spacing:0; margin-left:.25rem; }
.mp-kpi .l { font-size:.72rem; color:var(--mp-muted); text-transform:uppercase; letter-spacing:.05em; font-weight:600; margin-top:.15rem; }
@media (max-width: 820px) { .mp-kpis { grid-template-columns:repeat(2,minmax(0,1fr)); } .mp-kpi { padding:.7rem; gap:.6rem; } .mp-kpi .v { font-size:1.25rem; } }
[data-baseweb="tab-list"] { gap:.3rem; }
[data-baseweb="tab"] { font-weight:600; padding:.55rem .9rem; }
/* active run in the history list: soft tint instead of solid primary so the gray caption stays readable */
[class*="st-key-open_"] button[kind="primary"], [class*="st-key-open_"] [data-testid="stBaseButton-primary"] {
  background: var(--mp-accent-soft) !important; color: inherit !important; border:1px solid var(--mp-accent) !important; }
[class*="st-key-open_"] button p { text-align:left; }
/* keep history row (title + delete) on one line in the sidebar, also on phones */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width:0 !important; }
.mp-idea { font-size:1.05rem; font-weight:600; margin:.2rem 0 0; }
"""


def icon(name: str) -> str:
    return f'<span class="mp-ico" aria-hidden="true">{escape(name)}</span>'


def header_html(missing: list[str]) -> str:
    def chip(ok: bool, text: str) -> str:
        return f'<span class="mp-chip {"ok" if ok else "bad"}">{escape(text)}</span>'

    chips = [chip(not missing, "API keys ready" if not missing else "API keys missing")]
    chips += [chip(False, f"{k} not set") for k in missing]
    return (f'<div class="mp-bar-top"><div class="mp-logo"><span class="mark">{icon("radar")}</span>'
            f'<span>Market<b>Pulse</b></span></div>'
            f'<div class="mp-chips" role="status">{"".join(chips)}</div></div>')


def hero_html() -> str:
    facts = [("travel_explore", "Real competitors and prices"), ("forum", "What customers complain about"),
             ("fact_check", "Every claim sourced")]
    f = "".join(f"<span>{icon(i)}{escape(t)}</span>" for i, t in facts)
    return ('<section class="mp-hero"><span class="eyebrow">AI market research</span>'
            '<h1>Know your market <em>before</em> you enter it.</h1>'
            '<p>Describe your business idea. A team of AI agents researches your competitors, their prices and what '
            'customers complain about, then hands you a sourced report with a 30-day launch plan.</p>'
            f'<div class="facts">{f}</div></section>')


def how_it_works_html() -> str:
    steps = [("travel_explore", "Research", "Finds real competitors, prices and channels via web search."),
             ("forum", "Listen", "Mines customer reviews for repeated complaints."),
             ("lightbulb", "Position", "Spots the market gap and a sharp positioning."),
             ("event_note", "Plan", "Writes a sourced report with a 30-day launch plan.")]
    cards = "".join(f'<div class="mp-step"><div class="ic">{icon(ic)}</div><div class="n">Step {i}</div>'
                    f'<div class="t">{t}</div><div class="d">{d}</div></div>'
                    for i, (ic, t, d) in enumerate(steps, 1))
    return f'<div class="mp-sec">How it works</div><div class="mp-steps">{cards}</div>'


def stepper_html(agents: list[str], done: int, active: int | None) -> str:
    items = []
    for i, name in enumerate(agents):
        if i < done and i != active:
            state, label, dot = "done", "Done", "✓"
        elif i == active:
            state, label, dot = "active", "Working", str(i + 1)
        else:
            state, label, dot = "pending", "Queued", str(i + 1)
        cur = ' aria-current="step"' if state == "active" else ""
        items.append(f'<li class="mp-node {state}"{cur}><span class="mp-dot">{dot}</span>'
                     f'<span class="mp-lbl"><span class="a">{escape(name)}</span><span class="s">{label}</span></span></li>')
    return f'<ol class="mp-pipe" aria-label="Agent pipeline">{"".join(items)}</ol>'


def live_indicator_html() -> str:
    """Static (identical every render, so the CSS animation is never restarted)."""
    return '<div class="mp-live" role="progressbar" aria-label="Research in progress"><span class="mp-spin"></span><div class="mp-track"><i></i></div></div>'


def tips_html(tips: list[str]) -> str:
    """Pure-CSS rotating tips (8 s each, 40 s cycle for 5 tips); static markup so it never restarts."""
    return f'<div class="mp-tips" aria-hidden="true">{"".join(f"<span>{escape(t)}</span>" for t in tips[:5])}</div>'


def run_head_html(title: str, sub: str) -> str:
    return (f'<div class="mp-run-head"><div class="eyebrow">Research in progress</div>'
            f'<div class="ttl">{escape(title)}</div><div class="mp-sub">{sub}</div></div>')


def now_html(agent: str | None, phrase: str, step_no: int, total: int, elapsed: str, ago: str, quiet: bool,
             starting: bool = False) -> str:
    who = f'<span class="who">{escape(agent)}</span> ' if agent and not starting else ""
    phrase = phrase[len(agent) + 1:] if agent and not starting and phrase.startswith(agent) else phrase
    step = "Starting up" if starting else f"Step {min(step_no, total)} of {total}"
    note = ("Still working. Long web lookups can go quiet for a while." if quiet else "Live updates appear below.")
    return (f'<div role="status" aria-live="off"><div class="mp-now">{who}{escape(phrase)}</div>'
            f'<div class="mp-beat"><span><span class="dot{" slow" if quiet else ""}"></span>{escape(step)}</span>'
            f'<span>Elapsed <b>{escape(elapsed)}</b></span><span>Last activity <b>{escape(ago)}</b></span>'
            f'<span>{escape(note)}</span></div></div>')


_TOOL_ICONS = {"Searching": "search", "Reading": "article"}


def feed_html(events: list[tuple[str, str, str]]) -> str:
    """events: (kind, agent, text); newest last."""
    if not events:
        return ('<p class="mp-sub">Waiting for the first update from the agents. The first lookups can take a moment.</p>'
                '<div class="mp-skel" style="width:80%"></div><div class="mp-skel" style="width:60%"></div>')
    rows = []
    for kind, agent, text in events:
        text = text.replace("`", "")
        if kind == "task":
            ic, body = "check", f'<span class="k">Finished</span> {escape(text)}'
        else:
            head, sep, rest = text.partition(": ")
            if sep and head in _TOOL_ICONS:
                ic, body = _TOOL_ICONS[head], f'<span class="k">{escape(head)}</span> {escape(rest)}'
            else:
                ic, body = "psychology", escape(text)
        rows.append(f'<li class="{"task" if kind == "task" else "step"}"><span class="ic">{icon(ic)}</span>'
                    f'<span><span class="who">{escape(agent or "Agent")}</span><span class="tx">{body}</span></span></li>')
    return f'<ul class="mp-feed">{"".join(rows)}</ul>'


def kpi_html(items: list[tuple]) -> str:
    """items: (label, value[, icon[, unit]])."""
    cells = []
    for it in items:
        l, v = it[0], it[1]
        ic = it[2] if len(it) > 2 and it[2] else "insights"
        unit = f" ({it[3]})" if len(it) > 3 and it[3] else ""
        cells.append(f'<div class="mp-kpi"><span class="ic">{icon(ic)}</span><div><div class="v">{escape(v)}</div>'
                     f'<div class="l">{escape(l + unit)}</div></div></div>')
    return f'<div class="mp-kpis">{"".join(cells)}</div>'


def result_head_html(title: str, sub: str) -> str:
    return f'<div class="mp-res-head"><div class="ttl">{escape(title)}</div><div class="sub">{escape(sub)}</div></div>'


def card_html(title: str, body: str, error: bool = False) -> str:
    ic = icon("error") if error else ""
    return f'<div class="mp-card{" err" if error else ""}" role="alert"><h4>{ic}{escape(title)}</h4>{escape(body)}</div>'
