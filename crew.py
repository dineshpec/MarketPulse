import os

from dotenv import load_dotenv
from crewai import Crew, LLM, Process

from .agents import build_agents
from .report_parse import strip_code_fence
from .schemas import CrewResult, ScoutInput
from .tasks import build_tasks
from .validate_report import validate_report
from .tools import REPORTS_DIR, build_tools
from .ui_helpers import CancelToken, CrewCancelled  # noqa: F401 (re-exported)


def get_llm() -> LLM:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if "/" not in model:
        model = f"openai/{model}"
    return LLM(model=model, api_key=key, temperature=0.2)


def _guard_llm(llm, token: CancelToken):
    """Make every LLM call check the token first (instance-level patch of call/acall)."""
    orig_call, orig_acall = llm.call, getattr(llm, "acall", None)

    def call(*a, **k):
        token.check()
        return orig_call(*a, **k)

    llm.call = call
    if orig_acall is not None:
        async def acall(*a, **k):
            token.check()
            return await orig_acall(*a, **k)
        llm.acall = acall
    return llm


def build_crew(inputs: ScoutInput, hierarchical: bool = False, pitch_deck: bool = False,
               step_callback=None, task_callback=None, cancel_token: CancelToken | None = None) -> Crew:
    """Build the crew. NOTE: inputs are applied at kickoff (crew.kickoff(inputs=inputs.model_dump())).

    cancel_token: cooperative cancellation, effective at the next LLM call or task boundary (see
    run_crew). Verified against crewai 1.15.28: an exception raised in a step_callback is
    swallowed by the agent executor's flow listener, so the reliable hooks are the task callback
    (propagates out of kickoff) and the LLM call wrapper (propagates after the executor's retries).
    """
    llm = get_llm()
    if cancel_token is not None:
        _guard_llm(llm, cancel_token)
        user_step, user_task = step_callback, task_callback

        def step_callback(step, role=None):  # noqa: F811 - checks token first (best effort, may be swallowed)
            cancel_token.check()
            if user_step:
                user_step(step, role)

        def task_callback(out):  # noqa: F811 - raising here DOES abort kickoff
            cancel_token.check()
            if user_task:
                user_task(out)
    tools = build_tools()
    # step_callback(step, role): each agent gets its own closure so events name the real agent.
    agents = build_agents(llm, tools, pitch_deck=pitch_deck, step_callback=step_callback)
    tasks = build_tasks(agents, pitch_deck=pitch_deck)
    kwargs = dict(agents=list(agents.values()), tasks=tasks, verbose=True,
                  task_callback=task_callback)
    if hierarchical:
        # Crew-level callback only reaches agents without their own (i.e. the manager).
        mgr_cb = (lambda step: step_callback(step, "Manager")) if step_callback else None
        kwargs.update(process=Process.hierarchical, manager_llm=llm, step_callback=mgr_cb)
    else:
        kwargs.update(process=Process.sequential)
    return Crew(**kwargs)


def run_crew(inputs: ScoutInput, hierarchical: bool = False, pitch_deck: bool = False,
             step_callback=None, task_callback=None, cancel_token: CancelToken | None = None) -> CrewResult:
    """Run the crew. Cancelling (cancel_token) takes effect at the next LLM call or task end,
    not instantly: an in-flight LLM/tool call finishes first. Raises CrewCancelled."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "report.md"
    if report_path.exists():
        report_path.unlink()
    crew = build_crew(inputs, hierarchical, pitch_deck, step_callback, task_callback, cancel_token)
    if cancel_token is not None:
        cancel_token.check()
    output = crew.kickoff(inputs=inputs.model_dump())

    outs = list(output.tasks_output or [])
    by_role = {getattr(t.agent, "role", None): t for t in crew.tasks}
    writer_task = by_role.get("Report Writer")
    deck_task = by_role.get("Pitch Deck Designer") if pitch_deck else None

    def _raw(task):
        out = getattr(task, "output", None)
        return getattr(out, "raw", None) if out is not None else None

    writer_raw = _raw(writer_task) or (outs[-1].raw if outs else (output.raw or ""))
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
    else:
        report = writer_raw
    clean = strip_code_fence(report)
    if clean != report or not report_path.exists():
        report = clean
        report_path.write_text(report, encoding="utf-8")
    deck = strip_code_fence(_raw(deck_task)) if deck_task is not None and _raw(deck_task) else None
    warnings = validate_report(report)  # advisory only: never fails the run
    return CrewResult(report_markdown=report, pitch_deck_markdown=deck,
                      report_path=str(report_path), warnings=warnings)
