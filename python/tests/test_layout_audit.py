"""check_layout() and the rules it guards: no text over text, no text off the figure, no mark outside its plot,
for every chart and the hard cases in tokens/fixtures/stress.json (drawn the same way in R)."""

import json
from pathlib import Path

import pandas as pd
import pytest

import hairline as hl
from hairline.errors import HairlineLayoutError

CASES = json.loads((Path(__file__).parent / "fixtures" / "stress.json").read_text())["cases"]


@pytest.fixture(autouse=True)
def plain():
    hl.use(brand=False)


def test_check_layout_finds_text_over_text_and_marks_outside():
    figure = hl.figure("Two labels on one spot")
    figure.ax.annotate("Overlapping label", (0.5, 0.5))
    figure.ax.annotate("Overlapping label", (0.5, 0.5))
    figure.ax.scatter([0.0, 1.0], [0.0, 1.0], s=200)
    figure.ax.set_xlim(0, 1)
    figure.ax.set_ylim(0, 1)
    rules = {finding["rule"] for finding in hl.check_layout(figure)}
    assert rules == {"text_overlap", "mark_outside"}


@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_hard_cases_draw_without_collisions_or_are_refused_plainly(case, tmp_path, monkeypatch):
    if "host" in case:
        from hairline import host
        path = tmp_path / "context.json"
        path.write_text(json.dumps(case["host"]))
        monkeypatch.setenv(host.ENVIRONMENT, str(path))
        monkeypatch.setattr(host, "_state", {**host._state, "path": None, "context": None})
    try:
        figure = getattr(hl, case["chart"])(pd.DataFrame(case["data"]), **case["args"], size=case["size"])
        found = hl.check_layout(figure)
    except HairlineLayoutError as error:
        assert "hairline:" in str(error) and ("use a wider size" in str(error) or "Shorten" in str(error))
        return
    assert found == []


def test_counts_tick_at_whole_numbers_and_years_keep_their_order():
    data = pd.DataFrame({"year": ["2021", "2019", "2020"], "count": [1, 2, 3]})
    figure = hl.bars(data, "year", "count")
    figure.figure.canvas.draw()
    assert all(value == round(value) for value in figure.ax.get_yticks())
    assert [label.get_text() for label in figure.ax.get_xticklabels()] == ["2019", "2020", "2021"]


def test_many_named_groups_share_one_colour_and_long_names_wrap():
    groups = [f"Group {index} with a long name" for index in range(10)]
    data = pd.DataFrame({"group": [name for name in groups for _ in range(5)], "value": range(50)})
    rows = hl.charts.spread.spread_spec(data, "group", "value")["rows"]
    assert len({row["color"] for row in rows}) == 1
    figure = hl.raincloud(data[data["group"].isin(groups[:4])], "group", "value", size="onehalf")
    figure.figure.canvas.draw()
    assert any("\n" in label.get_text() for label in figure.ax.get_xticklabels())
    assert hl.check_layout(figure) == []
