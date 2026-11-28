"""Process diagram: who does which step (one lane per role), in which order (stages left to right), and how each
step hands on to the next. Steps can be highlighted (what changed) or tentative (absent, to be clarified), and a
note numbers a step and explains it below the lanes. Sections stack versions of one process (before and after) on
the same lanes and stages."""

from __future__ import annotations

import numbers
from collections.abc import Sequence

import pandas as pd

from hairline.charts.common import check_columns, group_names, ordered_names
from hairline.charts.diagrams_alt import process_description
from hairline.charts.process_geometry import process_drawing
from hairline.charts.process_routes import route_kind
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.settings import current_settings

STATUSES = ("highlight", "tentative")


def status_of(value: object, what: str) -> str | None:
    """A step's or flow's status: 'highlight', 'tentative', or None for a plain one (an empty cell)."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or str(value) == "":
        return None
    if str(value) not in STATUSES:
        raise ValueError(f"hairline: process: {what} has status {value!r}; use 'highlight', 'tentative' or leave it "
                         "empty")
    return str(value)


def text_of(value: object) -> str:
    return "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)


def section_steps(rows: pd.DataFrame, columns: dict, lanes: list[str], where: str) -> list[dict]:
    names = rows[columns["step"]].astype(str).tolist()
    repeated = [name for name in dict.fromkeys(names) if names.count(name) > 1]
    if repeated:
        raise ValueError(f"hairline: process: step {repeated[0]!r} appears twice{where}; name each step once")
    return [{"name": name, "lane": lanes.index(str(record[columns["lane"]])),
             "status": status_of(record[columns["status"]], f"step {name!r}") if columns["status"] else None,
             "note_text": text_of(record[columns["note"]]) if columns["note"] else "",
             "stage": record[columns["stage"]] if columns["stage"] else None}
            for name, (_, record) in zip(names, rows.iterrows(), strict=True)]


def section_flows(rows: pd.DataFrame | None, steps: list[dict], columns: dict, where: str) -> list[dict]:
    if rows is None:
        return []
    index = {step["name"]: position for position, step in enumerate(steps)}
    flows, seen = [], set()
    for _, record in rows.iterrows():
        ends = [str(record[columns[end]]) for end in ("source", "target")]
        unknown = [name for name in ends if name not in index]
        if unknown:
            raise ValueError(f"hairline: process: a flow names {unknown[0]!r}, which is not a step{where}; steps: "
                             f"{', '.join(index)}")
        if ends[0] == ends[1]:
            raise ValueError(f"hairline: process: the flow from {ends[0]!r} returns to itself{where}")
        if tuple(ends) in seen:
            raise ValueError(f"hairline: process: the flow from {ends[0]!r} to {ends[1]!r} appears twice{where}")
        seen.add(tuple(ends))
        flows.append({"source": index[ends[0]], "target": index[ends[1]],
                      "label": text_of(record[columns["label"]]) if columns["label"] else "",
                      "status": status_of(record[columns["flow_status"]], f"the flow from {ends[0]!r}")
                      if columns["flow_status"] else None})
    return flows


def derived_stages(count: int, flows: list[dict], where: str) -> list[int]:
    """Each step one stage after the latest step that hands on to it (the longest path), steps nothing hands on to at
    stage 0; a loop has no order and is an error."""
    incoming = [[flow["source"] for flow in flows if flow["target"] == step] for step in range(count)]
    stages: list[int | None] = [None] * count
    for _ in range(count):
        for step in range(count):
            if stages[step] is None and all(stages[source] is not None for source in incoming[step]):
                stages[step] = max((stages[source] + 1 for source in incoming[step]), default=0)
    if None in stages:
        raise ValueError(f"hairline: process: the flows run in a loop{where}; give stage= to place the steps")
    return stages


def given_stages(sections: list[dict], column: str) -> None:
    """Stages from the data, as positions: the distinct values in order become stages 0, 1, 2, …"""
    values = [step["stage"] for section in sections for step in section["steps"]]
    if any(not isinstance(value, numbers.Real) or isinstance(value, bool) or pd.isna(value) for value in values):
        raise ValueError(f"hairline: process: '{column}' needs a number for every step (1, 2, 3, … from left to "
                         "right)")
    places = {value: position for position, value in enumerate(sorted(set(values)))}
    for section in sections:
        for step in section["steps"]:
            step["stage"] = places[step["stage"]]


def check_places(section: dict, lanes: list[str], where: str) -> None:
    """One step per lane and stage, and flows that run left to right or up and down within a stage without
    crossing another step."""
    cells: dict[tuple[int, int], str] = {}
    for step in section["steps"]:
        cell = (step["lane"], step["stage"])
        if cell in cells:
            raise ValueError(f"hairline: process: {cells[cell]!r} and {step['name']!r} share lane "
                             f"{lanes[cell[0]]!r} and stage {cell[1] + 1}{where}; give them different stages")
        cells[cell] = step["name"]
    for flow in section["flows"]:
        source, target = section["steps"][flow["source"]], section["steps"][flow["target"]]
        if target["stage"] < source["stage"]:
            raise ValueError(f"hairline: process: the flow from {source['name']!r} to {target['name']!r} runs back "
                             f"from stage {source['stage'] + 1} to {target['stage'] + 1}{where}; flows run left to "
                             "right, or up and down within a stage")
        route_kind(source, target, set(cells), where)


def number_notes(sections: list[dict]) -> None:
    """Notes numbered 1, 2, … in reading order: by section, then stage, then lane."""
    number = 0
    for section in sections:
        noted = sorted((step for step in section["steps"] if step["note_text"]),
                       key=lambda step: (step["stage"], step["lane"]))
        section["notes"] = []
        for step in noted:
            number += 1
            step["note"] = number
            section["notes"].append({"number": number, "text": step["note_text"], "status": step["status"]})


def process_spec(steps: pd.DataFrame, flows: pd.DataFrame | None, columns: dict,
                 lanes: Sequence[str] | None) -> dict:
    """Lanes, the number of stages and each section's steps (lane, stage, status, note number) and flows."""
    check_columns(steps, [columns[key] for key in ("lane", "step", "stage", "section", "status", "note")])
    if flows is not None:
        check_columns(flows, [columns[key] for key in ("source", "target", "label", "section")])
    status = columns["status"]
    columns = {**columns, "flow_status": status if flows is not None and status in flows.columns else None}
    names = ordered_names(steps[columns["lane"]].astype(str), lanes, "process", columns["lane"], complete=True)
    section = columns["section"]
    sections = []
    for name in group_names(steps[section]) if section else [None]:
        where = f" in section {name!r}" if section else ""
        rows = steps[steps[section].astype(str) == name] if section else steps
        found = section_steps(rows, columns, names, where)
        moved = flows if flows is None or not section else flows[flows[section].astype(str) == name]
        sections.append({"name": name, "steps": found, "flows": section_flows(moved, found, columns, where),
                         "where": where})
    if columns["stage"]:
        given_stages(sections, columns["stage"])
    for entry in sections:
        if not columns["stage"]:
            for step, stage in zip(entry["steps"], derived_stages(len(entry["steps"]), entry["flows"], entry["where"]),
                                   strict=True):
                step["stage"] = stage
        check_places(entry, names, entry.pop("where"))
    number_notes(sections)
    return {"lanes": names, "stages": 1 + max(step["stage"] for entry in sections for step in entry["steps"]),
            "sections": sections, "accent": lone_color()}


def process(steps: pd.DataFrame, flows: pd.DataFrame | None = None, *, lane: str = "lane", step: str = "step",
            stage: str | None = None, section: str | None = None, status: str | None = None,
            note: str | None = None, source: str = "source", target: str = "target", label: str | None = None,
            lanes: Sequence[str] | None = None, title: str | None = None, subtitle: str | None = None,
            caption: str | None = None, size: str = "double") -> HairlineFigure:
    """One row of `steps` per step: its `lane` (who does it) and its name in `step`. `flows` hands on from
    `source` to `target` (step names), `label` naming how. Without `stage` each step stands one stage after the
    latest step handing on to it; with it, its numbers place the steps left to right, and a flow within a stage
    runs up or down. `status` ('highlight' or 'tentative', in `steps` and, where it has that column, in `flows`)
    marks what changed and what is absent or open; `note` numbers a step and lists its text below the lanes.
    `section` stacks versions of the process (before, after) on the same lanes; `flows` then needs that column
    too. `lanes` orders the lanes (the rest follow in data order)."""
    columns = {"lane": lane, "step": step, "stage": stage, "section": section, "status": status, "note": note,
               "source": source, "target": target, "label": label}
    spec = process_spec(steps, flows, columns, lanes)
    result = figure(title or "Process", subtitle=subtitle, caption=caption, size=size)
    result.description = process_description(spec, current_settings().locale)
    result.draw(0, lambda box, measure, style: process_drawing(spec, box, measure, style))
    return fit_height(result)
