"""table() and report(): tables in hairline's typography for documents, figures and tables numbered in the locale."""

import pandas as pd
import pytest

import hairline as hl
from hairline.charts.table import table_spec
from hairline.charts.table_geometry import fitted_widths
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box

STYLE = {"base": 9.0}


def measure(text: str, role: str, weight: int | None = None) -> float:
    return 4.0 * len(text)


def counts() -> pd.DataFrame:
    return pd.DataFrame({"Year": ["2024", "2025"], "Cases": [1234, 98], "Share": [0.125, 0.5]})


def test_numbers_are_formatted_in_the_locale_with_each_columns_own_decimals():
    hl.use(brand=False, locale="de")
    spec = table_spec(counts())
    assert spec["rows"] == [["2024", "1 234", "0,13"], ["2025", "98", "0,50"]]
    assert spec["align"] == ["left", "right", "right"]


def test_text_that_is_a_formatted_number_aligns_as_a_number():
    hl.use(brand=False)
    spec = table_spec(pd.DataFrame({"Level": ["1", "2"], "Days covered": ["12%", "100%"], "Note": ["a", "b"]}))
    assert spec["align"] == ["left", "right", "left"]


def test_bold_rows_by_position_or_first_column():
    hl.use(brand=False)
    assert table_spec(counts(), bold_rows=["2025"])["bold"] == [1]
    with pytest.raises(ValueError, match="bold_rows names 'x'"):
        table_spec(counts(), bold_rows=["x"])


def test_headings_wrap_before_the_first_column_and_a_table_too_wide_is_refused():
    hl.use(brand=False)
    spec = table_spec(pd.DataFrame({"A": ["x"], "A rather long heading": [1]}))
    natural = fitted_widths(spec, Box(0, 0, 1000, 100), measure, STYLE)
    assert natural == [4.0, 4.0 * len("A rather long heading")]
    wrapped = fitted_widths(spec, Box(0, 0, 70, 100), measure, STYLE)
    assert wrapped[1] < natural[1]
    with pytest.raises(HairlineLayoutError, match="even with wrapped headings"):
        fitted_widths(table_spec(pd.DataFrame({"First": ["a" * 40], "Second": ["b" * 40]})), Box(0, 0, 100, 100),
                      measure, STYLE)


def test_describe_table_passes_straight_in_and_keeps_its_indents():
    hl.use(brand=False)
    cohort = pd.DataFrame({"arm": ["A", "B"] * 6, "sex": ["F", "M", "M"] * 4, "age": range(12)})
    table = hl.study(cohort, group="arm", variables=["age", "sex"]).describe().table
    figure = hl.table(table, "Characteristics", footnotes=["IQR: interquartile range."], caption="Synthetic data.")
    figure.figure.canvas.draw()
    texts = [shape for shape in figure.shapes if shape["kind"] == "text"]
    female = next(shape for shape in texts if shape["text"] == "F")
    header = next(shape for shape in texts if shape["text"] == "Characteristic")
    assert female["x"] > header["x"]
    assert figure.caption == "IQR: interquartile range.\nSynthetic data."
    assert len([shape for shape in figure.shapes if shape.get("role") == "rule"]) == 3


def test_html_export_writes_a_real_table(tmp_path):
    hl.use(brand=False)
    figure = hl.table(counts(), "Cases per year", bold_rows=[1])
    (path,) = hl.save(figure, tmp_path / "cases", formats=["html"])
    page = path.read_text(encoding="utf-8")
    assert "<table>" in page and "<th" in page and ">1,234</td>" in page
    assert 'font-weight:600;">98</td>' in page


def test_report_numbers_figures_and_tables_apart_in_the_locale(tmp_path):
    hl.use(brand=False, locale="de")
    report = hl.report("Qualitätsbericht")
    report.add(hl.bars(pd.DataFrame({"a": ["x", "y"]}), "a"), "Fälle")
    report.add(hl.table(counts(), "Fälle pro Jahr"))
    report.add(hl.bars(pd.DataFrame({"a": ["x"]}), "a"))
    assert [label for _, label, _ in report.numbered()] == ["Abbildung 1", "Tabelle 1", "Abbildung 2"]
    page = report.write(tmp_path / "report.html").read_text(encoding="utf-8")
    assert "<b>Tabelle 1.</b> Fälle pro Jahr" in page and page.count("data:image/png;base64,") == 2
    text = report.write(tmp_path / "report.md").read_text(encoding="utf-8")
    assert text.startswith("# Qualitätsbericht") and "**Abbildung 2.** Count by a" in text
    with pytest.raises(ValueError, match="makes .md or .html files"):
        report.write(tmp_path / "report.docx")
