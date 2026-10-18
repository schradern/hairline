"""Panel headers: name, qualifier and key numbers, moving the key numbers to a second line when they do not fit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from hairline.layout.measure import text_width


@dataclass(frozen=True)
class PanelHeader:
    name: str
    qualifier: str | None = None
    stats: tuple[tuple[str, str], ...] = ()
    key: str | None = None
    x_title: str | None = None


@dataclass(frozen=True)
class Run:
    text: str
    x: float
    line: int
    style: dict


@dataclass
class ComposedHeader:
    runs: list[Run] = field(default_factory=list)
    lines: int = 1
    dropped: list[str] = field(default_factory=list)


def measure(text: str, style: dict) -> float:
    return text_width(text, style["family"], style["size"], style["weight"])


def value_style(label: str, key: str | None, styles: dict) -> dict:
    return styles["key_value"] if label == key else styles["stat_value"]


def pair_runs(pairs: Sequence[tuple[str, str]], x: float, line: int, styles: dict, gap: float,
              key: str | None = None) -> list[Run]:
    runs = []
    for index, (label, value) in enumerate(pairs):
        if index:
            x += gap
        runs.append(Run(f"{label} ", x, line, styles["stat_label"]))
        x += measure(f"{label} ", styles["stat_label"])
        runs.append(Run(value, x, line, value_style(label, key, styles)))
        x += measure(value, value_style(label, key, styles))
    return runs


def pairs_width(pairs: Sequence[tuple[str, str]], styles: dict, gap: float, key: str | None = None) -> float:
    widths = [measure(f"{label} ", styles["stat_label"]) + measure(value, value_style(label, key, styles))
              for label, value in pairs]
    return sum(widths) + gap * max(len(widths) - 1, 0)


def name_runs(header: PanelHeader, left: float, letter: str | None, styles: dict, gaps: dict) -> list[Run]:
    runs, x = [], left
    if letter:
        runs.append(Run(letter, x, 0, styles["letter"]))
        x += measure(letter, styles["letter"]) + gaps["letter"]
    runs.append(Run(header.name, x, 0, styles["name"]))
    x += measure(header.name, styles["name"])
    if header.qualifier:
        x += gaps["qualifier"]
        runs.append(Run(header.qualifier, x, 0, styles["qualifier"]))
    return runs


def compose_header(header: PanelHeader, left: float, right: float, letter: str | None, styles: dict,
                   gaps: dict) -> ComposedHeader:
    """Name and qualifier on line 1; numbers right on line 1, else left on line 2, else dropped."""
    runs = name_runs(header, left, letter, styles, gaps)
    composed = ComposedHeader(runs=runs)
    if not header.stats:
        return composed
    last = runs[-1]
    name_end = last.x + measure(last.text, last.style)
    stats, key = list(header.stats), header.key
    if name_end + gaps["stats_min"] + pairs_width(stats, styles, gaps["pair"], key) <= right:
        start = right - pairs_width(stats, styles, gaps["pair"], key)
        composed.runs += pair_runs(stats, start, 0, styles, gaps["pair"], key)
        return composed
    while stats and left + pairs_width(stats, styles, gaps["pair"], key) > right:
        composed.dropped.insert(0, stats.pop()[0])
    composed.runs += pair_runs(stats, left, 1, styles, gaps["pair"], key)
    composed.lines = 2 if stats else 1
    return composed
