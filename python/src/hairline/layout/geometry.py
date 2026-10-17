"""Pure frame geometry in pt, origin top-left; mirrored by the R package."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from importlib import resources


@dataclass(frozen=True)
class FontMetrics:
    cap_height: float
    descender: float
    ascender: float


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class FrameInput:
    width_pt: float
    height_pt: float
    base_size: float
    sizes: dict[str, float]
    title_lines: int = 1
    subtitle_lines: int = 0
    legend_rows: int = 0
    caption_lines: int = 0
    panel_rows: int = 1
    panel_columns: int = 1
    panel_header_lines: tuple[int, ...] = ()
    y_title: bool = False
    x_title: bool = False
    x_tick_labels: bool = True
    y_label_width_pt: float = 0.0
    y_labels: bool = True
    column_label_widths: tuple[float, ...] = ()
    x_tick_rows: tuple[bool, ...] = ()


@dataclass
class FrameLayout:
    left: float
    right: float
    plot_left: float
    title_baselines: list[float] = field(default_factory=list)
    subtitle_baselines: list[float] = field(default_factory=list)
    legend_row_centers: list[float] = field(default_factory=list)
    panel_header_baselines: list[list[float]] = field(default_factory=list)
    panels: list[Box] = field(default_factory=list)
    y_title_left: float | None = None
    y_title_baseline: float | None = None
    x_title_baseline: float | None = None
    caption_baselines: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["panels"] = [[box.x, box.y, box.width, box.height] for box in self.panels]
        return data


def load_font_metrics() -> FontMetrics:
    source = resources.files("hairline") / "data" / "fonts" / "metrics.json"
    values = json.loads(source.read_text(encoding="utf-8"))
    return FontMetrics(values["cap_height"], values["descender"], values["ascender"])


def frame_input_from_dict(values: dict) -> FrameInput:
    tuples = {key: tuple(values.get(key, ())) for key in ("panel_header_lines", "column_label_widths", "x_tick_rows")}
    return FrameInput(**{**values, **tuples})


class Stack:
    """Walks down the figure, placing text lines and gaps."""

    def __init__(self, top: float, metrics: FontMetrics, line_gap: float):
        self.y, self.metrics, self.line_gap = top, metrics, line_gap

    def lines(self, size: float, count: int) -> list[float]:
        baselines = []
        for index in range(count):
            if index:
                self.y += size * self.line_gap
            baselines.append(self.y + size * self.metrics.cap_height)
            self.y = baselines[-1] + size * self.metrics.descender
        return baselines

    def centered_rows(self, size: float, count: int, gap: float) -> list[float]:
        height, centers = size * (self.metrics.cap_height + self.metrics.descender), []
        for index in range(count):
            if index:
                self.y += gap
            centers.append(self.y + height / 2)
            self.y += height
        return centers

    def skip(self, amount: float) -> None:
        self.y += amount
