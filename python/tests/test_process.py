import json
from pathlib import Path

import pandas as pd
import pytest

import hairline as hl
from hairline.charts.process import derived_stages
from hairline.charts.process_routes import head, path, rounded
from hairline.interactive import figure_targets

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "process.json").read_text(encoding="utf-8"))


def steps(**columns) -> pd.DataFrame:
    rows = {"lane": ["Ward", "Laboratory", "Ward", "Physician"],
            "step": ["Draw sample", "Analyse", "See result", "Read result"],
            "status": ["", "", "highlight", "tentative"],
            "note": ["", "Runs around the clock.", "", "Not yet on the phone."]}
    return pd.DataFrame({**rows, **columns})


def flows(**columns) -> pd.DataFrame:
    rows = {"source": ["Draw sample", "Analyse", "See result"], "target": ["Analyse", "See result", "Read result"],
            "how": ["Courier", "", "Phone"], "status": ["", "highlight", "tentative"]}
    return pd.DataFrame({**rows, **columns})


def shapes(figure, role: str) -> list[dict]:
    figure.figure.canvas.draw()
    return [shape for shape in figure.shapes if shape.get("role") == role]


def texts(figure, part: str) -> list[str]:
    figure.figure.canvas.draw()
    return [shape["text"] for shape in figure.shapes if shape.get("part") == part]


@pytest.mark.parametrize("route", FIXTURE["routes"], ids=lambda route: f"{route['source']}-{route['target']}")
def test_routes_match_the_shared_fixture(route):
    places = FIXTURE["places"]
    cells = {tuple(cell) for cell in FIXTURE["cells"]}
    corners = path(places[route["source"]], places[route["target"]], cells, FIXTURE["turns"], "")
    line, tip = head(rounded(corners, FIXTURE["radius"], FIXTURE["steps"]), FIXTURE["head"])
    assert [value for point in line for value in point] == \
        pytest.approx([value for point in route["line"] for value in point])
    assert [value for point in tip for value in point] == \
        pytest.approx([value for point in route["tip"] for value in point])


def test_stages_follow_the_longest_path_in_the_shared_fixture():
    assert derived_stages(len(FIXTURE["places"]), FIXTURE["flows"], "") == FIXTURE["stages"]


def test_steps_stand_in_their_lanes_and_stages():
    figure = hl.process(steps(), flows(), status="status", note="note", label="how")
    assert texts(figure, "lane") == ["Ward", "Laboratory", "Physician"]
    boxes = {shape["series"]: shape["points"] for shape in shapes(figure, "step")}
    lefts = [boxes[name][0][0] for name in ("Draw sample", "Analyse", "See result", "Read result")]
    assert lefts == sorted(lefts) and len(set(lefts)) == 4
    assert boxes["Draw sample"][0][1] == pytest.approx(boxes["See result"][0][1])


def test_status_marks_steps_and_flows():
    figure = hl.process(steps(), flows(), status="status", note="note", label="how")
    accent = hl.current_settings().accent or hl.current_settings().palette[0]
    boxes = {shape["series"]: shape for shape in shapes(figure, "step")}
    assert boxes["See result"]["edge_width"] > boxes["Draw sample"]["edge_width"]
    assert "edge" not in boxes["Read result"]
    assert [shape["dash"] for shape in shapes(figure, "step_edge")] == [[2.0, 2.0]]
    lines = shapes(figure, "flow")
    assert lines[1]["width"] > lines[0]["width"] and lines[1]["color"] != lines[0]["color"]
    assert "dash" in lines[2] and accent


def test_notes_are_numbered_in_reading_order_and_listed():
    figure = hl.process(steps(), flows(), status="status", note="note", label="how")
    assert texts(figure, "marker") == ["1", "2", "1", "2"]
    assert texts(figure, "note") == ["Runs around the clock.", "Not yet on the phone."]
    assert texts(figure, "flow_label") == ["Courier", "Phone"]


def test_a_flow_within_a_stage_runs_up_or_down():
    data = pd.DataFrame({"lane": ["Laboratory", "Ward"], "step": ["Phone", "Take call"], "stage": [1, 1]})
    figure = hl.process(data, pd.DataFrame({"source": ["Phone"], "target": ["Take call"]}), stage="stage",
                        lanes=["Ward", "Laboratory"])
    line = shapes(figure, "flow")[0]["points"]
    assert line[0][0] == pytest.approx(line[-1][0]) and line[-1][1] < line[0][1]


def test_sections_stack_versions_on_the_same_lanes():
    data = pd.concat([steps(version="Before"), steps(version="After")])
    moved = pd.concat([flows(version="Before"), flows(version="After").iloc[[0, 2, 1]]])
    figure = hl.process(data, moved, section="version", note="note")
    assert texts(figure, "section") == ["Before", "After"]
    assert texts(figure, "marker") == ["1", "2", "1", "2", "3", "4", "3", "4"]
    assert figure.description == ("Process diagram. Lanes: Ward, Laboratory, Physician. Before: 4 steps, 3 flows. "
                                  "After: 4 steps, 3 flows.")


def test_steps_are_tooltip_targets_with_their_lane_and_note():
    figure = hl.process(steps(), flows(), note="note")
    tips = {series["name"]: tip["text"] for series in figure_targets(figure)["series"] for tip in series["tips"]}
    assert tips["Analyse"] == "Analyse\nLaboratory\nRuns around the clock."


def test_the_description_is_german_in_a_german_figure():
    hl.use(brand=False, locale="de")
    try:
        figure = hl.process(steps(), flows(), status="status")
        assert figure.description == ("Prozessdiagramm. Bahnen: Ward, Laboratory, Physician. 4 Schritte, "
                                      "3 Übergänge. Hervorgehoben: See result.")
    finally:
        hl.use(brand=False)


@pytest.mark.parametrize(("data", "moved", "options", "message"), [
    (steps(status=["", "", "new", ""]), None, {"status": "status"}, "status 'new'"),
    (steps(step=["A", "A", "B", "C"]), None, {}, "appears twice"),
    (steps(), flows(target=["Analyse", "Nowhere", "Read result"]), {}, "'Nowhere', which is not a step"),
    (steps(), flows(target=["Analyse", "Analyse", "Read result"]), {}, "returns to itself"),
    (steps(), pd.DataFrame({"source": ["Analyse", "Draw sample"], "target": ["Draw sample", "Analyse"]}), {},
     "in a loop"),
    (steps(stage=[1, 2, 1, 3]), None, {"stage": "stage"}, "share lane 'Ward' and stage 1"),
    (steps(stage=[1, 2, 3, 4]), pd.DataFrame({"source": ["Analyse"], "target": ["Draw sample"]}),
     {"stage": "stage"}, "runs back from stage 2 to 1"),
    (steps(stage=["a", "b", "c", "d"]), None, {"stage": "stage"}, "needs a number"),
])
def test_process_refuses_what_it_cannot_draw(data, moved, options, message):
    with pytest.raises(ValueError, match=message):
        hl.process(data, moved, **options)


def test_a_flow_that_would_cross_a_step_is_an_error():
    data = pd.DataFrame({"lane": ["Ward", "Ward", "Ward"], "step": ["A", "B", "C"], "stage": [1, 2, 3]})
    with pytest.raises(ValueError, match="from 'A' to 'C' would cross another step"):
        hl.process(data, pd.DataFrame({"source": ["A"], "target": ["C"]}), stage="stage")


def test_too_many_stages_for_the_width_is_a_layout_error():
    data = pd.DataFrame({"lane": ["Ward"] * 12, "step": [f"Step {index}" for index in range(12)]})
    moved = pd.DataFrame({"source": data["step"][:-1].tolist(), "target": data["step"][1:].tolist()})
    with pytest.raises(hl.HairlineLayoutError, match="12 stages need"):
        hl.process(data, moved, size="single")
