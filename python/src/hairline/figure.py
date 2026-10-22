"""figure(): a matplotlib figure laid out by hairline's frame on every draw."""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from hairline.fonts import register_fonts
from hairline.layout.draw import FrameArtist
from hairline.layout.engine import HairlineLayout
from hairline.layout.legend import LegendItem, validate_items
from hairline.layout.panels import PanelHeader
from hairline.settings import Settings, check_positive, current_settings
from hairline.style import rcparams_for
from hairline.tokens import load_tokens

LAYOUTS = ("compose", "grid", "pair", "rows")
MM_PER_INCH = 25.4
MAX_AXIS_DIGITS = 10


@dataclass
class HairlineFigure:
    figure: Figure
    axes: list[Axes]
    settings: Settings
    title: str
    subtitle: str | None = None
    caption: str | None = None
    columns: int = 1
    sharex: bool = False
    sharey: bool = False
    panel_letters: bool = False
    headers: dict[int, PanelHeader] = field(default_factory=dict)
    y_title_text: str | None = None
    x_title_text: str | None = None
    legend_items: list[LegendItem] | None = None
    collect_legend: bool = False
    percent_axes: set[tuple[int, str]] = field(default_factory=set)
    axis_digits: dict[tuple[int, str], int] = field(default_factory=dict)
    auto_limits: dict[tuple[int, str], bool] = field(default_factory=dict)
    applied_limits: dict[tuple[int, str], tuple[float, float]] = field(default_factory=dict)
    light_slot_done: set[int] = field(default_factory=set)
    point_done: set[int] = field(default_factory=set)
    handed_off: bool = False
    legend_placed: list = field(default_factory=list)
    line_widths: dict[int, float] = field(default_factory=dict)
    highlight_spec: dict | None = None
    focus_done: set[int] = field(default_factory=set)
    entity_done: set[int] = field(default_factory=set)
    references: list = field(default_factory=list)
    extra_legend_items: list[LegendItem] = field(default_factory=list)
    frame_artist: FrameArtist = field(default_factory=FrameArtist)
    report: dict = field(default_factory=dict)
    bare_panels: dict[int, float | None] = field(default_factory=dict)
    plot_boxes: list = field(default_factory=list)
    drawings: dict = field(default_factory=dict)
    shapes: list = field(default_factory=list)
    table_spec: dict | None = None
    category_axes: dict = field(default_factory=dict)
    table_value_xs: list = field(default_factory=list)
    table_keys: list[str] = field(default_factory=list)
    min_plot: float | None = None
    fitted_height: str | None = None

    def __post_init__(self) -> None:
        self.figure.add_artist(self.frame_artist)

    @property
    def ax(self) -> Axes:
        return self.axes[0]

    def panel_header(self, index: int, name: str, qualifier: str | None = None,
                     stats: Sequence[tuple[str, str]] = (), key: str | None = None,
                     x_title: str | None = None) -> None:
        """Name, optional qualifier and key numbers ('Label', 'value') above panel `index`; `key` marks one.
        `x_title` goes under this panel's own x-axis numbers (its unit, when panels measure different things)."""
        self.check_index(index)
        pairs = tuple((str(label), str(value)) for label, value in stats)
        if key is not None and key not in [label for label, _ in pairs]:
            raise ValueError(f"hairline: key {key!r} is not one of the key numbers: "
                             f"{', '.join(label for label, _ in pairs)}")
        self.headers[index] = PanelHeader(name, qualifier, pairs, key, x_title)

    def check_index(self, index: int) -> None:
        if not 0 <= index < len(self.axes):
            raise IndexError(f"hairline: panel {index} does not exist; this figure has {len(self.axes)} panels")

    def bare(self, index: int, aspect: float | None = None) -> None:
        """Draw panel `index` without axes, ticks or grid; `aspect` (height/width) centres a fixed-shape plot area."""
        self.check_index(index)
        if aspect is not None and aspect <= 0:
            raise ValueError(f"hairline: bare panel {index}: aspect must be positive, got {aspect}")
        self.bare_panels[index] = aspect

    def draw(self, index: int, shapes) -> None:
        """Draw panel `index` from `shapes(box, measure, style)`, a function returning shapes in pt (see drawing.py)."""
        self.check_index(index)
        self.bare_panels.setdefault(index, None)
        self.drawings[index] = shapes

    def categories(self, index: int, labels: Sequence[str], which: str = "x") -> None:
        """Label positions 0, 1, … of panel `index`'s axis with `labels`; hairline then leaves those ticks alone."""
        self.check_index(index)
        self.category_axes[(index, which)] = [str(label) for label in labels]

    def table(self, rows: Sequence[tuple[str, str, Sequence[tuple[float, str]]]], heading: str | None = None) -> None:
        """Rows (label, colour, [(x, text), ...]) under the x-axis, each text centred at its x (number at risk)."""
        self.table_spec = {"heading": heading, "rows": [(str(label), color, [(float(x), str(text)) for x, text in
                                                                             values]) for label, color, values in rows]}

    def highlight(self, series: Sequence[str] | None = None, panels: Sequence[int | str] | None = None) -> None:
        """Keep these series (legend labels) or panels (index or name) in colour; draw the rest in context grey."""
        self.highlight_spec = {"series": list(series) if series else None, "panels": list(panels) if panels else None}

    def reference(self, y: float | None = None, x: float | None = None, label: str | None = None,
                  panels: Sequence[int] | None = None, legend_label: str | None = None) -> None:
        """Thin dashed reference line (threshold, target) with an optional label at its end."""
        from hairline.focus import add_reference
        add_reference(self, y, x, label, panels, legend_label)

    def y_title(self, text: str) -> None:
        self.y_title_text = text

    def x_title(self, text: str) -> None:
        self.x_title_text = text

    def legend(self, items: Sequence[tuple[str, str, str]] | None = None) -> None:
        """Legend row under the header: explicit (kind, colour, label) items, or collected from the axes."""
        self.collect_legend = items is None
        self.legend_items = None if items is None else validate_items(items)

    def percent_axis(self, index: int, which: str = "y", digits: int | None = None) -> None:
        """Treat panel `index`'s values on axis `which` ("y" or "x") as shares and label them as percentages.

        `digits` fixes the decimals of the values a reader looks up (tooltips of interactive output), so that
        89.6 % never reads as 90 % next to a 90 % target. By default they follow the shared digits rule. Ticks keep
        their own decimals, set by the step between them."""
        self.percent_axes.add((index, which))
        self.set_axis_digits(index, which, digits)

    def number_axis(self, index: int, which: str = "y", digits: int | None = None) -> None:
        """Label panel `index`'s values on axis `which` ("y" or "x") as plain numbers (undoing `percent_axis`).

        `digits` fixes the decimals of the values a reader looks up (tooltips of interactive output); by default
        they follow the shared digits rule. Ticks keep their own decimals, set by the step between them."""
        self.percent_axes.discard((index, which))
        self.set_axis_digits(index, which, digits)

    def set_axis_digits(self, index: int, which: str, digits: int | None) -> None:
        if digits is None:
            self.axis_digits.pop((index, which), None)
            return
        if isinstance(digits, bool) or not isinstance(digits, int) or not 0 <= digits <= MAX_AXIS_DIGITS:
            raise ValueError(f"hairline: digits must be a whole number from 0 to {MAX_AXIS_DIGITS}, "
                             f"got {digits!r} for panel {index}, axis {which!r}")
        self.axis_digits[(index, which)] = digits

    def resize(self, width_mm: float | None = None, height_mm: float | None = None) -> HairlineFigure:
        """Set the figure's width and/or height in mm, like `hl_save(width_mm =, height_mm =)` in R. A chart whose
        height follows its content (forest, spread, ...) is fitted again for a new width unless a height is given.
        Axes panels still keep their least plot height (`spacing.min_plot_height` x the base size): a figure too
        short for it grows."""
        for value, name in ((width_mm, "width_mm"), (height_mm, "height_mm")):
            if value is not None:
                check_positive(value, name)
        width, height = (value * MM_PER_INCH for value in self.figure.get_size_inches())
        self.figure.set_size_inches((width_mm or width) / MM_PER_INCH, (height_mm or height) / MM_PER_INCH)
        if self.fitted_height and width_mm is not None and height_mm is None:
            from hairline.drawing import fit_height
            fit_height(self, shrink=self.fitted_height == "fit")
        return self

    def layout_report(self) -> dict:
        """Frame positions in pt from the top-left corner, as of the last draw."""
        return dict(self.report)


RASTER_FORMATS = ("png", "tif", "tiff", "jpg", "jpeg", "webp", "raw", "rgba")


def check_raster_size(fig: Figure, dpi: float, format_name: str) -> None:
    """A raster beyond the pixel budget (about an A0 poster at 600 dpi) is refused before its buffer exists: its
    memory grows with width x height x dpi², so a size in the wrong unit or a stray dpi could fill the machine."""
    if format_name.lower() not in RASTER_FORMATS:
        return
    width, height = fig.get_size_inches()
    megapixels, limit = width * height * dpi * dpi / 1e6, load_tokens()["export"]["max_megapixels"]
    if megapixels > limit:
        raise ValueError(f"hairline: a {width * MM_PER_INCH:.0f} x {height * MM_PER_INCH:.0f} mm figure at {dpi:g} "
                         f"dpi is {megapixels:,.0f} megapixels, more than the {limit:,} a raster image may have; "
                         f"lower the dpi or the size (in mm)")


def saved_format(fname: object, format_name: str | None) -> str:
    if format_name:
        return format_name
    suffix = Path(fname).suffix.lstrip(".") if isinstance(fname, str | os.PathLike) else ""
    return suffix or matplotlib.rcParams["savefig.format"]


def saved_dpi(fig: Figure, dpi: object) -> float:
    dpi = matplotlib.rcParams["savefig.dpi"] if dpi is None else dpi
    return fig.dpi if dpi == "figure" else float(dpi)


class HostFigure(Figure):
    """A matplotlib figure that, inside a host document, hands itself to the host after each save."""

    def savefig(self, fname, *args, **kwargs):
        check_raster_size(self, saved_dpi(self, kwargs.get("dpi")), saved_format(fname, kwargs.get("format")))
        result = super().savefig(fname, *args, **kwargs)
        owner = getattr(self, "hairline_figure", None)
        if owner is not None:
            from hairline.host import hand_off
            hand_off(owner)
        return result


def size_settings(size: str, width_mm: float | None, height_mm: float | None) -> tuple[float, float, Settings]:
    presets = load_tokens()["sizes"]
    if size not in presets:
        raise ValueError(f"hairline: unknown size {size!r}; use one of {', '.join(sorted(presets))}")
    for value, name in ((width_mm, "width_mm"), (height_mm, "height_mm")):
        if value is not None:
            check_positive(value, name)
    preset, settings = presets[size], current_settings()
    from hairline.host import host_context
    context = host_context()
    width = width_mm or (context.width_mm if context else None) or preset["width_mm"]
    height = height_mm or preset.get("height_mm") or width * preset["aspect"]
    if not settings.base_size_explicit:
        settings = replace(settings, base_size=float(preset["base_size"]))
    return width, height, settings


def grid_shape(panels: int, layout: str, columns: int | None) -> tuple[int, bool, bool]:
    if layout not in LAYOUTS:
        raise ValueError(f"hairline: unknown layout {layout!r}; use one of {', '.join(LAYOUTS)}")
    if panels < 1:
        raise ValueError(f"hairline: a figure needs at least one panel, got panels={panels}")
    shapes = {"rows": (1, True, True), "pair": (2, False, True), "grid": (math.ceil(math.sqrt(panels)), True, True),
              "compose": (min(panels, 2), False, False)}
    default_columns, sharex, sharey = shapes[layout]
    return (columns or default_columns), sharex, sharey


def create_axes(fig: Figure, panels: int, sharex: bool, sharey: bool) -> list[Axes]:
    axes: list[Axes] = []
    for _ in range(panels):
        first = axes[0] if axes else None
        axes.append(fig.add_axes((0.1, 0.1, 0.8, 0.8), sharex=first if sharex else None,
                                 sharey=first if sharey else None))
    return axes


def figure(title: str, subtitle: str | None = None, caption: str | None = None, size: str = "onehalf",
           width_mm: float | None = None, height_mm: float | None = None, panels: int = 1, layout: str = "rows",
           columns: int | None = None, panel_letters: bool = False) -> HairlineFigure:
    """Create a figure whose title, legend row, panels and caption follow hairline's frame."""
    register_fonts()
    columns, sharex, sharey = grid_shape(panels, layout, columns)
    width, height, settings = size_settings(size, width_mm, height_mm)
    matplotlib.rcParams.update(rcparams_for(settings))
    fig = plt.figure(figsize=(width / MM_PER_INCH, height / MM_PER_INCH), FigureClass=HostFigure)
    axes = create_axes(fig, panels, sharex, sharey)
    hairline_figure = HairlineFigure(fig, axes, settings, title, subtitle, caption, columns, sharex, sharey,
                                     panel_letters)
    fig.hairline_figure = hairline_figure
    fig.set_layout_engine(HairlineLayout(hairline_figure))
    return hairline_figure


def frame(fig: Figure, title: str, subtitle: str | None = None, caption: str | None = None) -> HairlineFigure:
    """Apply the frame to an existing single-axes matplotlib figure (best effort)."""
    if len(fig.axes) != 1:
        raise ValueError(f"hairline: frame() expects a figure with one axes, this one has {len(fig.axes)}")
    register_fonts()
    hairline_figure = HairlineFigure(fig, list(fig.axes), current_settings(), title, subtitle, caption)
    fig.set_layout_engine(HairlineLayout(hairline_figure))
    return hairline_figure
