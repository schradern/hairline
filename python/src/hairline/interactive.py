"""Interactive HTML: the static SVG plus targets for tooltips and series highlighting, drawn
by a script shared with the R package. Targets are in pt from the figure's top-left corner."""

from __future__ import annotations

import base64
import json
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.collections import PathCollection
from matplotlib.colors import to_hex
from matplotlib.container import BarContainer

from hairline.fonts import face_weight
from hairline.marks import FIXED_WIDTH_IDS, SECONDARY_ID, STATIC_ID
from hairline.numbers import auto_digits, format_number, format_percent
from hairline.settings import role_size
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure

SNAP_DIGITS = 10


def number_texts(values, percent: bool, digits: int | None = None, locale: str | None = None) -> list[str]:
    """Values formatted with `digits` decimals, or the shared digits rule (percentages for share axes), in
    `locale` (the figure's own, so a later change of the session's settings does not reach it)."""
    array = np.asarray(values, dtype=float)
    if percent:
        digits = auto_digits(array * 100) if digits is None else digits
        return [format_percent(round(float(value), SNAP_DIGITS), digits, locale) for value in array]
    digits = auto_digits(array) if digits is None else digits
    return [format_number(round(float(value), SNAP_DIGITS), digits, locale) for value in array]


def axis_number_texts(figure: HairlineFigure, index: int, which: str, values) -> list[str]:
    """Values on panel `index`'s axis `which`, as that axis labels them (percent or number, its digits)."""
    key = (index, which)
    return number_texts(values, key in figure.percent_axes, figure.axis_digits.get(key), figure.settings.locale)


def is_date_axis(axis) -> bool:
    converter = axis.get_converter() if hasattr(axis, "get_converter") else axis.converter
    return converter is not None and type(converter).__module__ == "matplotlib.dates"


def date_texts(values, zone) -> list[str]:
    """ISO dates in the data's own time zone (matplotlib keeps it as the axis units), with the clock time when any
    point has one (and its seconds when any has those), so hourly or second-apart points stay apart. Times are
    rounded to the second first: matplotlib's day numbers leave microsecond noise."""
    import datetime

    import matplotlib.dates as dates
    zone = zone if isinstance(zone, datetime.tzinfo) else None
    moments = [(dates.num2date(float(value), tz=zone) + datetime.timedelta(microseconds=500_000)).replace(microsecond=0)
               for value in values]
    seconds = any(moment.second for moment in moments)
    timed = seconds or any((moment.hour, moment.minute) != (0, 0) for moment in moments)
    shape = "%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M" if timed else "%Y-%m-%d"
    return [moment.strftime(shape) for moment in moments]


def x_texts(figure: HairlineFigure, index: int, ax, values) -> list[str]:
    """X values as text: ISO dates on a date axis, category names on a category axis, else numbers."""
    categories = figure.category_axes.get((index, "x"))
    if categories:
        return [categories[int(round(value))] if 0 <= round(value) < len(categories) else "" for value in values]
    if is_date_axis(ax.xaxis):
        return date_texts(values, ax.xaxis.get_units())
    return axis_number_texts(figure, index, "x", values)


def tip_text(name: str, values: str) -> str:
    """'Series: x, y', or the values alone for a figure without a series name or title."""
    return f"{name}: {values}" if name else values


def series_name(label: str, figure: HairlineFigure, index: int) -> str:
    if label and not label.startswith("_"):
        return label
    header = figure.headers.get(index)
    return header.name if header else figure.title


def steps(xy: np.ndarray) -> np.ndarray:
    """A steps-post path: horizontal to the next x, then vertical."""
    if len(xy) < 2:
        return xy
    points = [xy[0]]
    for previous, current in zip(xy[:-1], xy[1:], strict=True):
        points += [[current[0], previous[1]], current]
    return np.asarray(points)


def finite_runs(xy: np.ndarray) -> list[np.ndarray]:
    """The stretches of a line between missing values, where matplotlib breaks it; missing points get no tip."""
    finite = np.flatnonzero(np.isfinite(xy).all(axis=1))
    if not len(finite):
        return []
    return [xy[run] for run in np.split(finite, np.flatnonzero(np.diff(finite) > 1) + 1)]


def line_targets(figure: HairlineFigure, index: int, ax, to_pt) -> list[dict]:
    found = []
    for line in ax.lines:
        if line.get_gid() in FIXED_WIDTH_IDS or line.get_gid() in (SECONDARY_ID, STATIC_ID):
            continue
        if line.get_linestyle() in ("None", "none", "", " "):
            continue
        xy = np.asarray(line.get_xydata(), dtype=float)
        runs = finite_runs(xy)
        if not runs:
            continue
        xy = np.concatenate(runs)
        paths = [steps(run) if line.get_drawstyle() == "steps-post" else run for run in runs]
        name = series_name(line.get_label(), figure, index)
        xs, ys = x_texts(figure, index, ax, xy[:, 0]), axis_number_texts(figure, index, "y", xy[:, 1])
        found.append({"name": name, "color": to_hex(line.get_color()),
                      "marks": [{"line": [to_pt(ax, point) for point in path], "width": line.get_linewidth()}
                                for path in paths],
                      "tips": [{"at": to_pt(ax, point), "text": tip_text(name, f"{x}, {y}")}
                               for point, x, y in zip(xy, xs, ys, strict=True)]})
    return found


def point_targets(figure: HairlineFigure, index: int, ax, to_pt) -> list[dict]:
    found = []
    for collection in ax.collections:
        offsets = np.asarray(collection.get_offsets(), dtype=float)
        offsets = offsets[np.isfinite(offsets).all(axis=1)] if offsets.ndim == 2 else offsets
        if not isinstance(collection, PathCollection) or collection.get_gid() == STATIC_ID or not len(offsets) \
                or not len(collection.get_facecolor()):
            continue
        name = series_name(collection.get_label(), figure, index)
        radius = float(np.sqrt(collection.get_sizes()[0]) / 2) if len(collection.get_sizes()) else 2.0
        xs = x_texts(figure, index, ax, offsets[:, 0])
        ys = axis_number_texts(figure, index, "y", offsets[:, 1])
        found.append({"name": name, "color": to_hex(collection.get_facecolor()[0]),
                      "marks": [{"dot": to_pt(ax, point), "r": radius} for point in offsets],
                      "tips": [{"at": to_pt(ax, point), "text": tip_text(name, f"{x}, {y}")}
                               for point, x, y in zip(offsets, xs, ys, strict=True)]})
    return found


def bar_targets(figure: HairlineFigure, index: int, ax, to_pt) -> list[dict]:
    found = []
    for container in ax.containers:
        if not isinstance(container, BarContainer):
            continue
        horizontal = getattr(container, "orientation", "vertical") == "horizontal"
        name = series_name(container.get_label(), figure, index)
        marks, tips, values = [], [], []
        for patch in container.patches:
            low, high = to_pt(ax, (patch.get_x(), patch.get_y() + patch.get_height())), to_pt(
                ax, (patch.get_x() + patch.get_width(), patch.get_y()))
            # A negative bar runs the other way; the target is the same box with its corners in order.
            left, top = min(low[0], high[0]), min(low[1], high[1])
            marks.append({"rect": [left, top, abs(high[0] - low[0]), abs(high[1] - low[1])]})
            values.append(patch.get_width() if horizontal else patch.get_height())
        axis = "x" if horizontal else "y"
        texts = axis_number_texts(figure, index, axis, values)
        centres = [patch.get_y() + patch.get_height() / 2 if horizontal else patch.get_x() + patch.get_width() / 2
                   for patch in container.patches]
        labels = category_texts(figure, index, "y" if horizontal else "x", centres)
        for mark, label, value in zip(marks, labels, texts, strict=True):
            x, y, width, height = mark["rect"]
            tips.append({"at": [x + width / 2, y], "text": tip_text(name, f"{label}, {value}")})
        found.append({"name": name, "color": to_hex(container.patches[0].get_facecolor()) if marks else "#000000",
                      "marks": marks, "tips": tips})
    return found


def category_texts(figure: HairlineFigure, index: int, axis: str, positions) -> list[str]:
    labels = figure.category_axes.get((index, axis)) or []
    return [labels[int(round(value))] if 0 <= round(value) < len(labels) else "" for value in positions]


def drawn_targets(figure: HairlineFigure) -> list[dict]:
    """Drawn charts mark their shapes with `series` (and one `tip` per series) while drawing."""
    found: dict[str, dict] = {}
    for shape in figure.shapes:
        if "series" not in shape:
            continue
        entry = found.setdefault(shape["series"], {"name": shape["series"], "color": shape.get("fill") or
                                                   shape.get("color"), "marks": [], "tips": []})
        if shape["kind"] == "polygon":
            entry["marks"].append({"polygon": shape["points"], "alpha": shape.get("alpha", 1.0)})
        elif shape["kind"] == "line":
            entry["marks"].append({"line": shape["points"], "width": shape["width"]})
        if "tip" in shape:
            entry["tips"].append({"at": shape["tip_at"], "text": shape["tip"]})
    return list(found.values())


def merged(series: list[dict]) -> list[dict]:
    """One entry per name: a group's line, points and bars highlight together."""
    by_name: dict[str, dict] = {}
    for entry in series:
        if entry["name"] in by_name:
            by_name[entry["name"]]["marks"] += entry["marks"]
            by_name[entry["name"]]["tips"] += entry["tips"]
        else:
            by_name[entry["name"]] = entry
    return list(by_name.values())


def legend_targets(figure: HairlineFigure) -> list[dict]:
    centers = figure.report.get("legend_row_centers", []) if figure.report else []
    line = role_size(figure.settings, "label") * (1 + load_tokens()["type"]["line_gap"])
    return [{"name": entry.item.label, "box": [entry.x, centers[entry.row] - line / 2, entry.right - entry.x, line]}
            for entry in figure.legend_placed if entry.row < len(centers)]


def rounded(value):
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, (list, tuple)):
        return [rounded(item) for item in value]
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    return value


def figure_targets(figure: HairlineFigure) -> dict:
    """Everything the shared script needs: size, style, plot boxes, series with marks and tips, legend boxes."""
    fig = figure.figure
    fig.canvas.draw()
    width, height = (float(value) * 72 for value in fig.get_size_inches())
    scale = 72 / fig.dpi

    def to_pt(ax, point) -> list[float]:
        x, y = ax.transData.transform(point)
        return [float(x) * scale, height - float(y) * scale]
    series: list[dict] = []
    for index, ax in enumerate(figure.axes):
        if index not in figure.drawings:
            series += line_targets(figure, index, ax, to_pt) + point_targets(figure, index, ax, to_pt)
            series += bar_targets(figure, index, ax, to_pt)
    series += drawn_targets(figure)
    neutral, rules = figure.settings.neutral, load_tokens()["interactive"]
    style = {"ink": neutral["ink"], "surface": neutral["surface"], "axis": neutral["axis"],
             "font": figure.settings.font, "size": role_size(figure.settings, "label"), "veil": rules["veil"],
             "hit": rules["hit_pt"]}
    return rounded({"version": 1, "width": width, "height": height, "style": style,
                    "panels": [[box.x, box.y, box.width, box.height] for box in figure.plot_boxes],
                    "series": merged(series), "legend": legend_targets(figure)})


def asset(name: str) -> str:
    return (resources.files("hairline") / "data" / "interactive" / name).read_text(encoding="utf-8")


FACE_WEIGHTS = (400, 500, 600)
FONT_FORMATS = {".ttf": ("font/ttf", "truetype"), ".otf": ("font/otf", "opentype")}


def bundled_font_files() -> list[tuple[list[int], str, bytes]]:
    weights = {"Regular": 400, "Medium": 500, "SemiBold": 600}
    folder = resources.files("hairline") / "data" / "fonts"
    return [([weights[file.split("-")[1].split(".")[0]]], ".ttf", (folder / file).read_bytes())
            for file in load_tokens()["interactive"]["fonts"]]


def installed_font_files(family: str) -> list[tuple[list[int], str, bytes]]:
    """The files matplotlib draws `family` with, per weight of the faces it has (one file may serve several); a
    collection (.ttc) cannot be embedded and is left to the reader's installed fonts."""
    from matplotlib.font_manager import FontProperties, findfont
    weights: dict[Path, list[int]] = {}
    for weight in sorted({face_weight(family, weight) for weight in FACE_WEIGHTS}):
        try:
            path = Path(findfont(FontProperties(family=family, weight=weight), fallback_to_default=False))
        except ValueError:
            continue
        if path.suffix.lower() in FONT_FORMATS:
            weights.setdefault(path, []).append(weight)
    return [(found, path.suffix.lower(), path.read_bytes()) for path, found in weights.items()]


def font_faces(family: str) -> str:
    """The figure's font as data URIs under its own name, so the page renders with the font the layout was
    measured with: the bundled files for the bundled family, else the installed files of the requested one."""
    bundled = family == load_tokens()["font"]["family"]
    faces = []
    for weights, suffix, data in bundled_font_files() if bundled else installed_font_files(family):
        media, kind = FONT_FORMATS[suffix]
        weight = f"{min(weights)} {max(weights)}" if len(weights) > 1 else str(weights[0])
        faces.append(f"@font-face{{font-family:'{family}';font-weight:{weight};"
                     f"src:url(data:{media};base64,{base64.b64encode(data).decode()}) format('{kind}')}}")
    return "".join(faces)


def figure_html(svg: str, targets: dict, family: str, alt: str = "") -> str:
    """One self-contained <figure>: static SVG, overlay, tooltip box, targets and script (embeddable as is)."""
    body = svg[svg.index("<svg"):]
    style = targets["style"]
    variables = f"--hl-ink:{style['ink']};--hl-surface:{style['surface']};--hl-axis:{style['axis']};" \
                f"--hl-font:'{style['font']}'"
    data = json.dumps(targets, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    label = alt.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return (f'<figure class="hairline-figure" style="{variables}" aria-label="{label}">'
            f'<style>{font_faces(family)}{asset("hairline.css")}</style>{body}'
            f'<svg class="hairline-overlay" viewBox="0 0 {targets["width"]} {targets["height"]}" '
            f'xmlns="http://www.w3.org/2000/svg"></svg><div class="hairline-tip"></div>'
            f'<script type="application/json" class="hairline-targets">{data}</script>'
            f'<script>{asset("hairline.js")}</script></figure>')


def page(title: str, fragment: str, surface: str = "#ffffff") -> str:
    safe = title.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe}</title>'
            f'<style>body{{margin:0;padding:16px;background:{surface}}}</style></head><body>{fragment}</body></html>\n')
