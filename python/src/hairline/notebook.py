"""Notebooks (Jupyter, VS Code): a figure or result shows itself when a cell ends with it, once, at its own size.

Inside a notebook kernel hairline keeps its figures out of matplotlib's automatic display, which would show every
figure a cell made (a result kept for later as well), crop it, and show it again beside an explicit display. A host
document (Paperings) collects figures from pyplot itself and keeps that behaviour."""

from __future__ import annotations

import base64
import html
import io
import sys
from typing import TYPE_CHECKING

from matplotlib.figure import Figure

from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure
    from hairline.study.result import Result


def in_notebook() -> bool:
    """True inside a notebook kernel (ipykernel), not in a terminal IPython or a plain script."""
    ipython = sys.modules.get("IPython")
    shell = ipython.get_ipython() if ipython is not None and hasattr(ipython, "get_ipython") else None
    return getattr(shell, "kernel", None) is not None


def keeps_display(fig: Figure) -> None:
    """Leave pyplot's figure list in a notebook kernel without a host, so the figure shows only when displayed."""
    from hairline.host import host_context
    if in_notebook() and host_context() is None:
        import matplotlib.pyplot as plt
        plt.close(fig)


def png_bytes(figure: HairlineFigure) -> bytes:
    """The figure as PNG at the notebook resolution, at its own size (no tight crop), on its own surface."""
    from hairline.figure import check_raster_size
    dpi = load_tokens()["notebook"]["dpi"]
    check_raster_size(figure.figure, dpi, "png")
    buffer = io.BytesIO()
    # Figure.savefig, not the host's: showing a figure in a notebook is not saving it for a document.
    Figure.savefig(figure.figure, buffer, format="png", dpi=dpi)
    return buffer.getvalue()


def figure_bundle(figure: HairlineFigure) -> tuple[dict, dict]:
    """The PNG (shown at the figure's size on a screen) and a one-line text for consoles."""
    width, height = figure.figure.get_size_inches()
    screen = load_tokens()["notebook"]["screen_dpi"]
    data = {"image/png": base64.b64encode(png_bytes(figure)).decode("ascii"), "text/plain": repr(figure)}
    return data, {"image/png": {"width": round(width * screen), "height": round(height * screen)}}


def result_html(result: Result) -> str:
    """The figure, the sentence and the table, in that order (as R Markdown shows a result), as plain HTML a
    notebook styles itself."""
    parts = []
    if result.figure is not None:
        data, metadata = figure_bundle(result.figure)
        size = metadata["image/png"]
        parts.append(f'<img src="data:image/png;base64,{data["image/png"]}" width="{size["width"]}" '
                     f'height="{size["height"]}" alt="{html.escape(result.figure.title)}">')
    parts += [f"<p>{html.escape(result.text)}</p>", result.table.to_html(index=False, border=0, escape=True)]
    return "\n".join(parts)
