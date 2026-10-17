import os
from pathlib import Path

from dotenv import load_dotenv
from crewai_tools import FileWriterTool, ScrapeWebsiteTool, SerperDevTool

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def build_tools() -> dict:
    """Return {'search','scrape','file_writer'}. Raises RuntimeError if SERPER_API_KEY missing."""
    load_dotenv()
    if not os.getenv("SERPER_API_KEY"):
        raise RuntimeError(
            "SERPER_API_KEY is not set. Get a key at https://serper.dev and add it to your .env file."
        )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "search": SerperDevTool(),
        "scrape": ScrapeWebsiteTool(),
        "file_writer": FileWriterTool(directory=str(REPORTS_DIR)),
    }
