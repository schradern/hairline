"""check_layout(): what a reader would see collide in a finished figure. Text over text, text off the figure and
marks outside their plot are findings; a figure hairline drew should have none. The R package checks the same
rules in hl_check_layout()."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from matplotlib.collections import Collection, PathCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text

from hairline.layout.geometry import load_font_metrics
from hairline.tokens import load_tokens

POINTS_PER_INCH = 72


@dataclass(frozen=True)
class Box:
    """A rectangle in pt from the figure's top-left corner."""
    left: float
    top: float
    right: float
    bottom: float

    def overlaps(self, other: Box, tolerance: float) -> bool:
        return (min(self.right, other.right) - max(self.left, other.left) > tolerance
                and min(self.bottom, other.bottom) - max(self.top, other.top) > tolerance)

    def beyond(self, outer: Box, tolerance: float) -> float:
        """How far this box reaches past `outer`, in pt (0 inside)."""
        return max(outer.left - self.left, self.right - outer.right, outer.top - self.top,
                   self.bottom - outer.bottom, 0.0) if not self.inside(outer, tolerance) else 0.0

    def inside(self, outer: Box, tolerance: float) -> bool:
        return (self.left >= outer.left - tolerance and self.right <= outer.right + tolerance
                and self.top >= outer.top - tolerance and self.bottom <= outer.bottom + tolerance)

    def rounded(self) -> list[float]:
        return [round(self.left, 2), round(self.top, 2), round(self.right, 2), round(self.bottom, 2)]


def to_box(fig: Figure, extent) -> Box:
    """A display-space bounding box as pt from the top-left corner."""
    scale, height = POINTS_PER_INCH / fig.dpi, fig.bbox.height
    return Box(extent.x0 * scale, (height - extent.y1) * scale, extent.x1 * scale, (height - extent.y0) * scale)


def ink_box(fig: Figure, text: Text, renderer) -> Box:
    """Where the text's glyphs reach: a line runs from its baseline up by the cap height and down by the
    descender (the font's full ascent and line gap never carry ink). Same box as R's hl_check_layout()."""
    box = to_box(fig, text.get_window_extent(renderer))
    size, metrics = text.get_fontsize(), load_font_metrics()
    if "\n" in text.get_text() or text.get_rotation() % 180:
        line = (box.bottom - box.top) / (text.get_text().count("\n") + 1)
        trim = max(0.0, line - size * (metrics.cap_height + metrics.descender)) / 2
        if text.get_rotation() % 180:
            return Box(box.left + trim, box.top, box.right - trim, box.bottom)
        return Box(box.left, box.top + trim, box.right, box.bottom - trim)
    _, _, descent = renderer.get_text_width_height_descent(text.get_text(), text.get_fontproperties(),
                                                            ismath=False)
    descent *= POINTS_PER_INCH / fig.dpi
    baseline = box.bottom - descent
    return Box(box.left, baseline - size * metrics.cap_height, box.right, baseline + size * metrics.descender)


def shown_texts(fig: Figure) -> list[Text]:
    texts = []
    for text in fig.findobj(Text):
        if text.get_text().strip() and text.get_visible() and all_visible(text) and (text.get_alpha() or 1) > 0:
            texts.append(text)
    return texts


def all_visible(artist) -> bool:
    """Tick labels of hidden axes or ticks keep their own visibility; their parents decide what is drawn."""
    axes = artist.axes
    return axes is None or axes.get_visible()


def text_findings(fig: Figure, renderer, tolerance: float) -> list[dict]:
    frame = Box(0, 0, fig.bbox.width * POINTS_PER_INCH / fig.dpi, fig.bbox.height * POINTS_PER_INCH / fig.dpi)
    placed = [(text.get_text(), ink_box(fig, text, renderer)) for text in shown_texts(fig)]
    findings = [{"rule": "text_outside", "text": label, "box": box.rounded()}
                for label, box in placed if not box.inside(frame, tolerance)]
    for index, (label, box) in enumerate(placed):
        for other_label, other in placed[index + 1:]:
            if box.overlaps(other, tolerance):
                findings.append({"rule": "text_overlap", "text": label, "other": other_label,
                                 "box": box.rounded(), "other_box": other.rounded()})
    return findings


def point_boxes(fig: Figure, collection: PathCollection) -> list[Box]:
    """Each dot of a scatter with its radius."""
    offsets = collection.get_offset_transform().transform(collection.get_offsets())
    sizes = collection.get_sizes()
    scale, height = POINTS_PER_INCH / fig.dpi, fig.bbox.height
    boxes = []
    for index, (x, y) in enumerate(offsets):
        if not np.isfinite([x, y]).all():
            continue
        radius = np.sqrt(sizes[index % len(sizes)] if len(sizes) else 0) / 2
        left, top = x * scale, (height - y) * scale
        boxes.append(Box(left - radius, top - radius, left + radius, top + radius))
    return boxes


def mark_boxes(fig: Figure, artist, renderer) -> list[Box]:
    if isinstance(artist, PathCollection) and len(artist.get_offsets()):
        return point_boxes(fig, artist)
    if isinstance(artist, Line2D | Patch | Collection):
        extent = artist.get_window_extent(renderer)
        if extent.width >= 0 and extent.height >= 0 and np.isfinite([extent.x0, extent.y0, extent.x1, extent.y1]).all():
            return [to_box(fig, extent)]
    return []


def mark_findings(fig: Figure, renderer, tolerance: float) -> list[dict]:
    findings = []
    for index, ax in enumerate(fig.axes):
        if not ax.get_visible() or not ax.axison and not ax.patch.get_visible():
            continue
        plot = to_box(fig, ax.get_window_extent(renderer))
        for artist in [*ax.collections, *ax.lines, *ax.patches]:
            if not artist.get_visible() or artist.get_gid() == "hairline-occluder":
                continue
            for box in mark_boxes(fig, artist, renderer):
                reach = box.beyond(plot, tolerance)
                if reach:
                    findings.append({"rule": "mark_outside", "panel": index, "mark": type(artist).__name__,
                                     "reach": round(reach, 2), "box": box.rounded()})
                    break
    return findings


def check_layout(figure) -> list[dict]:
    """What a reader would see collide in the finished figure: text over text, text off the figure, marks outside
    their plot. Each finding names its rule and where (pt from the top-left corner); an empty list means none."""
    fig = getattr(figure, "figure", figure)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    tolerance = load_tokens()["audit"]["tolerance"]
    return text_findings(fig, renderer, tolerance) + mark_findings(fig, renderer, tolerance)
