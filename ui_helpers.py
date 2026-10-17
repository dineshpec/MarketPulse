"""Pure, Streamlit-free helpers for the MarketPulse UI (testable without a running app)."""
from __future__ import annotations

import json
import os
import queue
import re
import threading
from dataclasses import dataclass, field

AGENT_ORDER = ["Market Researcher", "Review Analyst", "Strategy Analyst", "Report Writer"]
DECK_AGENT = "Pitch Deck Designer"
MANAGER_LABEL = "Manager"
MAX_FIELD = 500
REQUIRED_KEYS = {"OPENAI_API_KEY": "OpenAI", "SERPER_API_KEY": "Serper (web search)"}


def missing_keys(env=None) -> list[str]:
    env = os.environ if env is None else env
    return [k for k in REQUIRED_KEYS if not str(env.get(k, "")).strip()]


def validate_inputs(business_idea: str, city: str, target_customer: str, known_competitors: str = "") -> list[str]:
    """Return a list of human-readable problems (empty list means valid)."""
    errs = []
    for label, v in (("Business idea", business_idea), ("City", city), ("Target customer", target_customer)):
        v = (v or "").strip()
        if not v:
            errs.append(f"{label} is required.")
        elif len(v) > MAX_FIELD:
            errs.append(f"{label} is too long (max {MAX_FIELD} characters).")
    if len((known_competitors or "").strip()) > 2000:
        errs.append("Known competitors is too long (max 2000 characters).")
    return errs


def agent_sequence(pitch_deck: bool = False) -> list[str]:
    """Agents in task order. The deck task runs before the report writer (writer is always last)."""
    if pitch_deck:
        return AGENT_ORDER[:-1] + [DECK_AGENT, AGENT_ORDER[-1]]
    return list(AGENT_ORDER)


def _agent_name(obj) -> str:
    a = getattr(obj, "agent", None)
    if isinstance(a, str):
        return a.strip() or "Agent"
    for attr in ("role", "name"):
        v = getattr(a, attr, None)
        if v:
            return str(v).strip()
    return "Agent"


def _short(text, n=220) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 3] + "..."


class CrewCancelled(Exception):
    """Raised (by CancelToken.check) to abort a crew run the user cancelled."""


class CancelToken:
    """Thread-safe cancel flag shared by the UI thread and the crew worker thread.

    Cancellation is cooperative: it takes effect at the next agent step / LLM call / task
    boundary, not instantly. An LLM or tool call already in flight runs to completion.
    """

    def __init__(self):
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise CrewCancelled("Run cancelled by user.")


@dataclass
class Event:
    kind: str  # "step" | "task" | "done" | "error" | "cancelled"
    agent: str = ""
    text: str = ""
    payload: object = field(default=None, repr=False)


def _tool_arg(inp) -> str:
    """Pull the most meaningful argument (query / url) out of a tool input (dict, JSON string or text)."""
    if isinstance(inp, str):
        t = inp.strip()
        if t.startswith("{"):
            try:
                inp = json.loads(t)
            except ValueError:
                inp = t
    if isinstance(inp, dict):
        for k in ("search_query", "query", "q", "website_url", "url", "link", "website", "input"):
            if inp.get(k):
                return str(inp[k])
        vals = [str(v) for v in inp.values() if v]
        return vals[0] if vals else ""
    return str(inp or "")


def _host(url: str) -> str:
    m = re.match(r"\s*(?:https?://)?(?:www\.)?([^/\s?#]+)", url or "")
    return m.group(1) if m else (url or "")


def describe_tool_use(tool, inp) -> str:
    """Plain-words description of a tool call: 'Searching: x', 'Reading: example.com'."""
    name = str(tool or "").lower()
    arg = _short(_tool_arg(inp), 120)
    is_url = bool(re.match(r"\s*(https?://|www\.)", arg, re.I))
    if any(w in name for w in ("search", "serper", "google")) and not is_url:
        return f"Searching: {arg}" if arg else "Searching the web"
    if is_url or any(w in name for w in ("scrape", "website", "read", "fetch", "browse", "crawl")):
        return f"Reading: {_host(arg)}" if arg else "Reading a web page"
    return f"Using {tool}: {arg}" if arg else f"Using {tool}"


def format_step_event(step, role: str | None = None) -> Event:
    """Turn a CrewAI step object (AgentAction / AgentFinish / tool result / str) into an Event.

    CrewAI step objects carry no agent, so the caller passes the agent's role.
    """
    name = (role or "").strip() or _agent_name(step)
    tool = getattr(step, "tool", None)
    if tool:
        return Event("step", name, describe_tool_use(tool, getattr(step, "tool_input", "")))
    thought = getattr(step, "thought", None) or getattr(step, "text", None) or getattr(step, "output", None)
    return Event("step", name, _short(thought or step, 220))


STAGE_ACTIVITY = {
    "Market Researcher": "is searching the web for competitors, prices and channels",
    "Review Analyst": "is reading customer reviews to find repeated complaints",
    "Strategy Analyst": "is comparing the findings to spot a market gap",
    "Pitch Deck Designer": "is turning the findings into a pitch deck",
    "Report Writer": "is writing your sourced report",
    MANAGER_LABEL: "is planning and delegating the work",
}
TIPS = ["Reading competitor websites and price lists",
        "Web research can take several minutes, and it is normal for it to go quiet for a while",
        "You can leave this tab open and come back later",
        "Cross-checking prices and claims against their sources",
        "Cancel any time: your inputs are kept"]


def stage_headline(agent: str | None, starting: bool = False) -> str:
    if starting:
        return "Getting the research team ready"
    agent = agent or AGENT_ORDER[0]
    return f"{agent} {STAGE_ACTIVITY.get(agent, 'is working on your research')}"


def ago_label(seconds) -> str:
    try:
        s = max(0, int(seconds))
    except (TypeError, ValueError):
        return "just now"
    if s < 2:
        return "just now"
    return f"{elapsed_label(s)} ago"


_CUR = re.compile(r"(Rs\.?|INR|₹|US\$|\$|€|£|USD|EUR|GBP|CAD|AUD)\s*\d", re.I)
_CUR_AFTER = re.compile(r"\d\s*(Rs\.?|INR|USD|EUR|GBP)", re.I)
_UNIT = re.compile(r"(?:per|/|a)\s*([A-Za-z]+)", re.I)


def price_units(prices) -> tuple[str, str]:
    """(currency, unit) most common in price strings, e.g. ('Rs', 'meal'); blanks when absent."""
    from collections import Counter
    cur, unit = Counter(), Counter()
    for p in prices or []:
        p = str(p or "")
        m = _CUR.search(p) or _CUR_AFTER.search(p)
        if m:
            c = m.group(1)
            cur["Rs" if c.lower().rstrip(".") in ("rs", "inr") else c.upper() if c.isalpha() else c] += 1
        u = _UNIT.search(p)
        if u:
            unit[u.group(1).lower()] += 1
    return (cur.most_common(1)[0][0] if cur else "", unit.most_common(1)[0][0] if unit else "")


def format_task_event(task_output, hierarchical: bool = False) -> Event:
    raw = getattr(task_output, "raw", None) or str(task_output)
    # In hierarchical mode task_output.agent is the manager, not the worker: don't claim it.
    name = "Task" if hierarchical else _agent_name(task_output)
    return Event("task", name, _short(raw, 300), payload=raw)


def progress_fraction(done_tasks: int, total_tasks: int) -> float:
    if total_tasks <= 0:
        return 0.0
    return max(0.0, min(1.0, done_tasks / total_tasks))


def current_agent(done_tasks: int, pitch_deck: bool = False, hierarchical: bool = False,
                  last_role: str | None = None) -> str:
    """Label for the progress bar.

    Sequential: the agent whose task is next. Hierarchical: task order is chosen by the manager,
    so use the last worker role seen in step events, else "Manager delegating...".
    """
    total = len(agent_sequence(pitch_deck))
    done = min(max(done_tasks, 0), total)
    if hierarchical:
        role = (last_role or "").strip()
        if role and role != MANAGER_LABEL:
            return f"{role} ({done}/{total} tasks done)"
        return f"Manager delegating... ({done}/{total} tasks done)"
    return agent_sequence(pitch_deck)[min(done, total - 1)]


def friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "serper" in low:
        return "Serper search failed. Check `SERPER_API_KEY` in your `.env` file."
    if "openai_api_key" in low:
        return "OpenAI API key missing. Set `OPENAI_API_KEY` in your `.env` file and restart."
    if "401" in low or "authentication" in low or "incorrect api key" in low:
        return "A provider rejected the API key. Check `OPENAI_API_KEY` and `SERPER_API_KEY` in `.env`."
    if "429" in low or ("rate" in low and "limit" in low) or "quota" in low:
        return "Rate limit or quota reached. Wait a minute and try again."
    if "connection" in low or "timeout" in low or "timed out" in low:
        return "Could not reach the API. Check your internet connection and try again."
    return f"The research run failed: {msg or type(e).__name__}"




def start_crew_worker(run_fn, inputs, q: "queue.Queue", hierarchical=False, pitch_deck=False,
                      cancel_token: "CancelToken | None" = None) -> threading.Thread:
    """Run run_fn in a daemon thread; callbacks only put Events on q (no Streamlit calls).

    If cancel_token is given it is passed to run_fn as cancel_token=... and checked before every
    queued step/task event. Cancelling takes effect at the next agent step, LLM call or task
    boundary, not instantly: work already in flight finishes first. A cancelled run ends with
    Event("cancelled") instead of "error".
    """
    def on_step(s, role=None):
        if cancel_token is not None:
            cancel_token.check()
        q.put(format_step_event(s, role))

    def on_task(t):
        if cancel_token is not None:
            cancel_token.check()
        q.put(format_task_event(t, hierarchical))

    def worker():
        kwargs = dict(hierarchical=hierarchical, pitch_deck=pitch_deck,
                      step_callback=on_step, task_callback=on_task)
        if cancel_token is not None:
            kwargs["cancel_token"] = cancel_token  # only passed when used: old run_fn signatures still work
        try:
            res = run_fn(inputs, **kwargs)
            q.put(Event("done", payload=res))
        except CrewCancelled as e:
            q.put(Event("cancelled", text="Run cancelled.", payload=e))
        except Exception as e:  # noqa: BLE001
            # CrewAI can re-wrap errors raised in callbacks: a set token still means "cancelled".
            if cancel_token is not None and cancel_token.is_cancelled:
                q.put(Event("cancelled", text="Run cancelled.", payload=e))
            else:
                q.put(Event("error", text=friendly_error(e), payload=e))

    th = threading.Thread(target=worker, daemon=True, name="mp-crew-worker")
    th.start()
    return th


EXAMPLES: list[dict] = [
    {"label": "Millet meal boxes, Coimbatore",
     "business_idea": "Healthy millet-based meal boxes delivered to offices",
     "city": "Coimbatore",
     "target_customer": "Working professionals aged 25-40 who want healthy lunches",
     "known_competitors": "Freshmenu, Box8, local tiffin services"},
    {"label": "Pet grooming, Austin",
     "business_idea": "Premium mobile pet grooming",
     "city": "Austin",
     "target_customer": "Busy dog owners who value convenience",
     "known_competitors": "Petco, Fluffy Paws"},
    {"label": "Meeting-notes SaaS, Berlin",
     "business_idea": "AI meeting-notes app for small agencies",
     "city": "Berlin",
     "target_customer": "Founders and project managers at agencies with 5-20 people",
     "known_competitors": "Otter.ai, Fireflies, Fathom"},
    {"label": "Women's gym, Toronto",
     "business_idea": "Women-only boutique strength training studio",
     "city": "Toronto",
     "target_customer": "Women aged 25-45 new to weightlifting",
     "known_competitors": "GoodLife Fitness, Anytime Fitness"},
]


def elapsed_label(seconds) -> str:
    """Compact duration: 45s, 3m 05s, 1h 02m."""
    try:
        s = max(0, int(round(float(seconds))))
    except (TypeError, ValueError):
        return "0s"
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60:02d}s"
    return f"{s // 3600}h {(s % 3600) // 60:02d}m"


def idea_title(inputs, max_len: int = 60) -> str:
    """Short 'idea - city' title for the history list."""
    idea = " ".join(str(getattr(inputs, "business_idea", "") or "").split())
    city = " ".join(str(getattr(inputs, "city", "") or "").split())
    title = f"{idea} - {city}" if city else idea
    return title if len(title) <= max_len else title[: max_len - 3].rstrip() + "..."
