from crewai import Agent


def _bind(step_callback, role: str):
    """Per-agent step callback: CrewAI steps carry no agent, so close over the role."""
    if step_callback is None:
        return None
    return lambda step: step_callback(step, role)


def build_agents(llm, tools: dict, pitch_deck: bool = False, step_callback=None) -> dict:
    """Return dict keys: researcher, reviewer, strategist, writer (+ pitch if pitch_deck).

    step_callback, if given, is called as step_callback(step, role) for each agent step.
    """
    common = dict(llm=llm, verbose=True, allow_delegation=False)
    agents = {
        "researcher": Agent(
            role="Market Researcher",
            step_callback=_bind(step_callback, "Market Researcher"),
            goal="Find 3-5 real competitors for {business_idea} in {city} and collect their "
                 "prices, offers and sales channels, each with a source URL.",
            backstory="You are a meticulous local-market researcher. You only report facts you "
                      "found on real web pages and always keep the URL. You never invent prices.",
            tools=[tools["search"], tools["scrape"]], **common),
        "reviewer": Agent(
            role="Review Analyst",
            step_callback=_bind(step_callback, "Review Analyst"),
            goal="For each competitor, summarise what customers like and complain about "
                 "(especially {target_customer}), based on real reviews, with source URLs.",
            backstory="You mine reviews, forums and social posts to find recurring patterns in "
                      "customer sentiment. You only report what you actually read.",
            tools=[tools["search"], tools["scrape"]], **common),
        "strategist": Agent(
            role="Strategy Analyst",
            step_callback=_bind(step_callback, "Strategy Analyst"),
            goal="Build a competitor comparison matrix, identify the market gap and recommend "
                 "price and positioning for {business_idea} in {city}.",
            backstory="You are a sharp go-to-market strategist who turns research into clear, "
                      "defensible positioning. You rely only on the research handed to you.",
            tools=[], **common),
        "writer": Agent(
            role="Report Writer",
            step_callback=_bind(step_callback, "Report Writer"),
            goal="Produce a polished report.md with six sections and numbered sources, and "
                 "save it with the file writer tool.",
            backstory="You are a business writer who turns analysis into concise, scannable "
                      "reports where every price or claim is linked to a source.",
            tools=[tools["file_writer"]], **common),
    }
    if pitch_deck:
        agents["pitch"] = Agent(
            role="Pitch Deck Designer",
            step_callback=_bind(step_callback, "Pitch Deck Designer"),
            goal="Turn the research and strategy into a crisp 6-slide markdown pitch deck "
                 "for {business_idea}.",
            backstory="You are a startup storyteller who distils analysis into persuasive slides.",
            tools=[], **common)
    return agents
