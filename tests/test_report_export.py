import pytest

report_export = pytest.importorskip("marketpulse.report_export")


def test_pdf_bytes(good_report):
    out = report_export.markdown_to_pdf(good_report)
    assert isinstance(out, (bytes, bytearray)) and bytes(out).startswith(b"%PDF")


@pytest.mark.parametrize(
    "md",
    [
        "",
        "# Title with emoji \U0001F680 and Tamil தமிழ்\n\ntext “smart quotes” – dash ₹500 €5",
        "| a | b |\n|---|---|\n| x |",
        "A" * 5000,
        "https://example.com/" + "x" * 300,
    ],
)
def test_pdf_never_raises(md):
    assert bytes(report_export.markdown_to_pdf(md)).startswith(b"%PDF")


def test_extract_sources(good_report):
    src = report_export.extract_sources(good_report)
    assert len(src) == 3
    assert any("example.com/fluffy-paws" in str(s) for s in src)
