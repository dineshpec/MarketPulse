"""Offline tests for report parsing."""
import pandas as pd
import pytest

from marketpulse.report_parse import parse_competitors, parse_sections, price_chart_data, sources_with_titles

NUMBERED = """# Title

## 1. Key Competitors
| Competitor | Price (state the unit) | Channel | Strength | Weakness | Offers |
|---|---|---|---|---|---|
| Box8 | Rs 180 per meal | App | Fast | Pricey | 10% off |
| Millet Magic | ₹1,200/month | WhatsApp | Healthy | Small menu | - |
| Tiffin Co | Free trial | Web | Cheap | Slow | - |

## 2. What Customers Complain About
- Late delivery

## Sources
1. [Box8 site](https://box8.in/menu)
2. Millet Magic - https://millet.example.com/plans.
3. https://box8.in/menu
"""


def test_parse_sections_numbered(good_report):
    s = parse_sections(NUMBERED)
    assert "Key Competitors" in s and "What Customers Complain About" in s and "Sources" in s
    assert "Late delivery" in s["What Customers Complain About"]
    assert "Key Competitors" in parse_sections(good_report)


def test_parse_sections_bad_input():
    assert parse_sections(None) == {}
    assert parse_sections("no headings") == {}


def test_parse_competitors_prices_and_extras():
    df = parse_competitors(NUMBERED)
    assert list(df.columns[:6]) == ["Competitor", "Price", "Price Value", "Channel", "Strength", "Weakness"]
    assert "Offers" in df.columns
    assert df["Price Value"].tolist() == [180.0, 1200.0, None]
    assert df.loc[0, "Price"] == "Rs 180 per meal"
    assert df.loc[1, "Price"] == "₹1,200/month"


def test_parse_competitors_good_report(good_report):
    df = parse_competitors(good_report)
    assert df["Competitor"].tolist() == ["Fluffy Paws", "Pawfect Spa", "Bark & Bubbles"]
    assert df["Price Value"].tolist() == [65.0, 80.0, 45.0]
    assert df.loc[0, "Channel"] == ""  # column absent in this report


@pytest.mark.parametrize("md", [None, "", "no table", "## Key Competitors\nnone found", "## Key Competitors\n| a |\n|--|"])
def test_parse_competitors_never_raises(md):
    df = parse_competitors(md)
    assert df.empty and "Price Value" in df.columns and "Competitor" in df.columns


def test_price_chart_data():
    chart = price_chart_data(parse_competitors(NUMBERED))
    assert chart is not None and list(chart.columns) == ["Competitor", "Price Value"]
    assert chart["Competitor"].tolist() == ["Box8", "Millet Magic"]


def test_price_chart_data_too_few():
    assert price_chart_data(parse_competitors("")) is None
    assert price_chart_data(None) is None
    one = pd.DataFrame({"Competitor": ["A", "B"], "Price Value": [1.0, None]})
    assert price_chart_data(one) is None


def test_sources_with_titles_dedupes():
    assert sources_with_titles(NUMBERED) == [
        ("Box8 site", "https://box8.in/menu"),
        ("Millet Magic", "https://millet.example.com/plans"),
    ]


def test_sources_bare_url_uses_host(good_report):
    src = sources_with_titles(good_report)
    assert src[0] == ("example.com", "https://example.com/fluffy-paws")
    assert len(src) == 3
    assert sources_with_titles("nothing") == []


def test_strip_code_fence():
    from marketpulse.report_parse import strip_code_fence

    fenced = "```markdown\n## 1. Key Competitors\n\ntext\n```"
    assert strip_code_fence(fenced).startswith("## 1. Key Competitors")
    assert "```" not in strip_code_fence(fenced)
    plain = "## Market Gap\nno fences"
    assert strip_code_fence(plain) == plain
    assert strip_code_fence(None) == ""
