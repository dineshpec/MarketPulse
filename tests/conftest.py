import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

GOOD_REPORT = """# MarketPulse Report: Premium Pet Grooming in Austin

## Key Competitors
| Competitor | Price | Strength | Weakness |
|---|---|---|---|
| Fluffy Paws | $65 per groom | Convenient mobile vans | Slow booking |
| Pawfect Spa | $80 per groom | Luxury feel | Expensive add-ons |
| Bark & Bubbles | From $45 | Cheap and quick | Rushed service |

## What Customers Complain About
- Long wait times for appointments
- Hidden fees for matted fur

## Market Gap
No one offers transparent flat pricing with same-week booking.

## Recommended Positioning
The honest-price groomer: flat fees, online booking in 60 seconds.

## 30-Day Launch Plan
- Week 1: Register business, book van lease
- Week 2: Launch landing page and booking
- Week 3: Local Instagram campaign
- Week 4: Referral discount

## Sources
- https://example.com/fluffy-paws
- https://example.com/pawfect-spa
- https://example.com/bark-and-bubbles
"""


@pytest.fixture
def good_report():
    return GOOD_REPORT


@pytest.fixture
def dummy_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy")
    monkeypatch.setenv("SERPER_API_KEY", "dummy")


@pytest.fixture(autouse=True)
def _isolate_reports_dir(tmp_path, monkeypatch):
    """run_crew deletes reports/report.md up front; never let a test touch the real one."""
    import marketpulse.crew as crew_mod
    import marketpulse.tools as tools_mod

    monkeypatch.setattr(crew_mod, "REPORTS_DIR", tmp_path / "reports", raising=False)
    monkeypatch.setattr(tools_mod, "REPORTS_DIR", tmp_path / "reports", raising=False)
