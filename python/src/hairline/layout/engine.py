"""HairlineLayout: a matplotlib layout engine that applies the frame on every draw."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from matplotlib.layout_engine import LayoutEngine

from hairline.errors import HairlineLayoutError
from hairline.layout.apply import apply_frame

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


class HairlineLayout(LayoutEngine):
    _adjust_compatible = False
    _colorbar_gridspec = False

    def __init__(self, hairline_figure: HairlineFigure, **kwargs):
        super().__init__(**kwargs)
        self.hairline_figure = hairline_figure

    def execute(self, fig) -> None:
        """Lays out the frame. matplotlib drops a ValueError raised here and draws a blank figure, so every error
        but our own is passed on as a HairlineLayoutError that reaches savefig(), show() and notebooks."""
        try:
            dropped = apply_frame(self.hairline_figure)
        except HairlineLayoutError:
            raise
        except Exception as error:
            raise HairlineLayoutError(f"hairline: drawing the figure failed: {type(error).__name__}: {error}") \
                from error
        for panel, labels in dropped.items():
            warnings.warn(f"hairline: panel {panel} header: key numbers dropped because they do not fit: "
                          f"{', '.join(labels)}", UserWarning, stacklevel=2)
