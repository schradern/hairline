"""Draw frame artists in pt measured from the figure's top-left corner."""

from __future__ import annotations

from matplotlib.artist import Artist
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Transform


class FrameArtist(Artist):
    """Holds the frame's text and swatches; drawn after the layout engine has replaced its children.

    Its extent is the whole figure, because the frame's margins are part of the design: a tight bounding box
    (as used by Jupyter's inline display) then keeps the figure at its designed size instead of cropping it.
    """

    def __init__(self):
        super().__init__()
        self.children: list[Artist] = []
        self.set_in_layout(True)
        self.set_zorder(10)

    def get_window_extent(self, renderer=None):
        return self.figure.bbox

    def replace_children(self, children: list[Artist]) -> None:
        self.children = children
        self.stale = True

    def get_children(self) -> list[Artist]:
        return list(self.children)

    def draw(self, renderer) -> None:
        for child in self.children:
            child.draw(renderer)
        self.stale = False


def pt_transform(fig: Figure) -> Transform:
    """Transform mapping (x pt from left, y pt from top) to display coordinates."""
    height_inches = fig.get_size_inches()[1]
    return Affine2D().scale(1 / 72, -1 / 72).translate(0, height_inches) + fig.dpi_scale_trans


def add_text(fig: Figure, x: float, baseline: float, text: str, style: dict, align: str = "left") -> Text:
    """Place one line of text with its baseline at `baseline` pt."""
    artist = Text(x, baseline, text, transform=pt_transform(fig), ha=align, va="baseline",
                  fontfamily=style["family"], fontsize=style["size"], fontweight=style["weight"],
                  color=style["color"])
    artist.set_figure(fig)
    artist.set_in_layout(False)
    return artist


def add_line(fig: Figure, x0: float, y0: float, x1: float, y1: float, style: dict) -> Line2D:
    line = Line2D([x0, x1], [y0, y1], transform=pt_transform(fig), color=style["color"],
                  linewidth=style["width"], linestyle=style.get("dash", "-"), alpha=style.get("alpha", 1.0),
                  solid_capstyle="butt")
    line.set_figure(fig)
    line.set_in_layout(False)
    return line


def add_rect(fig: Figure, x: float, y: float, width: float, height: float, color: str) -> Rectangle:
    rect = Rectangle((x, y + height), width, -height, transform=pt_transform(fig), facecolor=color,
                     edgecolor="none", linewidth=0)
    rect.set_figure(fig)
    rect.set_in_layout(False)
    return rect
