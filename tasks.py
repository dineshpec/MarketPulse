from crewai import Task


def build_tasks(agents: dict, pitch_deck: bool = False) -> list:
    """Sequential order: research, reviews, strategy, [pitch deck], report (always last)."""
    research = Task(
        description=(
            "Research the competitive landscape for this business idea: {business_idea} in {city}, "
            "targeting {target_customer}. Known competitors (may be empty): {known_competitors}. "
            "Find 3-5 REAL competitors. For each give name, price (state the unit, e.g. per "
            "session, per month, per item), offers/promotions, sales channels, strength, weakness "
            "and the source URL for each fact. Never invent data."),
        expected_output=(
            "A Markdown table with exactly these columns: Competitor | Price (with unit) | Offers | "
            "Channel | Strength | Weakness | Source URL. Include at least 3 competitors (up to 5), "
            "each with a concrete price and a source URL. If fewer than 3 competitors with prices "
            "could be found, say so explicitly below the table instead of inventing data."),
        agent=agents["researcher"])
    reviews = Task(
        description=(
            "For each competitor found, research customer reviews and discussions in {city} "
            "(especially from {target_customer}). Summarise what customers like and complain "
            "about, with recurring themes and source URLs."),
        expected_output=(
            "Markdown with one '### <Competitor name>' heading per competitor, each followed by "
            "three bullet fields: '- Likes:', '- Complaints:', '- Source URLs:'. End with a "
            "'### Recurring themes' heading and a bulleted list of the top themes."),
        agent=agents["reviewer"], context=[research])
    strategy = Task(
        description=(
            "Using the research and reviews, create a comparison matrix, identify the market gap "
            "for {business_idea} in {city}, and recommend a price point and positioning for "
            "{target_customer}. Include a week-by-week 30-day launch plan."),
        expected_output=(
            "Markdown with these headings in order: '### Comparison Matrix' (a table), "
            "'### Market Gap', '### Recommended Price' (a number with its unit and a one-line "
            "rationale), '### Positioning' (one short statement), '### 30-Day Launch Plan' "
            "(bullets for Week 1, Week 2, Week 3, Week 4)."),
        agent=agents["strategist"], context=[research, reviews])
    tasks = [research, reviews, strategy]
    if pitch_deck:
        deck = Task(
            description=(
                "Create a 6-slide markdown pitch deck for {business_idea} in {city}. Slides: "
                "1 Problem, 2 Solution, 3 Market and Competitors, 4 Positioning and Pricing, "
                "5 30-Day Launch Plan, 6 Ask and Next Steps. Separate slides with a line "
                "containing only '---' and start each with a '## Slide N: Title' heading."),
            expected_output="Markdown with exactly 6 slides separated by '---'.",
            agent=agents["pitch"], context=[research, reviews, strategy])
        tasks.append(deck)
    write = Task(
        description=(
            "Write the final report for {business_idea} in {city} (target: {target_customer}) in "
            "markdown with exactly these sections: '## 1. Key Competitors' (a markdown table with "
            "columns Competitor | Price (state the unit) | Channel | Strength | Weakness), "
            "'## 2. What Customers Complain About', '## 3. Market Gap', "
            "'## 4. Recommended Positioning', '## 5. 30-Day Launch Plan' (week by week), and "
            "'## Sources' (numbered list of URLs). Every price or claim must cite a source number "
            "that maps to a URL in Sources. Save it using the file writer tool with filename "
            "'report.md' (overwrite=True), then output the full report markdown as your final answer. "
            "Output raw markdown only: do not wrap it in code fences. The competitor table has exactly "
            "those 5 columns (no extra link column); cite sources as [1], [2] after the claim."),
        expected_output=(
            "The complete report markdown with the 6 sections ('## 1. Key Competitors' through "
            "'## Sources'). Your final answer must be the full report markdown itself, not a "
            "confirmation message or summary of what you saved."),
        agent=agents["writer"], context=[research, reviews, strategy])
    tasks.append(write)
    return tasks
