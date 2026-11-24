"""What every study endpoint returns: one computation, five views of it."""

from __future__ import annotations

import os
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


@dataclass
class Result:
    """`figure` (or None), `table` of formatted strings, `values` for inline use, a sentence or two of `text`, and
    the unrounded `numbers` they are formatted from: per group n, rows left out as missing, the statistics and the
    test (method, statistic, df where defined, p; NaN when undefined)."""

    figure: HairlineFigure | None
    table: pd.DataFrame
    values: dict
    text: str
    numbers: dict

    def __repr__(self) -> str:
        return f"{self.text}\n\n{self.table.to_string(index=False)}"

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict:
        """A notebook shows the figure, the sentence and the table when a cell ends with the result."""
        from hairline.notebook import result_html
        return {"text/html": result_html(self), "text/plain": repr(self)}

    def save(self, name: str | os.PathLike, formats: Sequence[str] = ("pdf", "png"), table: bool = True,
             dpi: int | None = None, background: str | None = None) -> list[Path]:
        """The figure as `name.<format>` for each format and, with `table`, the table as `name.csv` (formatted
        values, as printed); returns the paths. A result without a figure writes its table only."""
        paths = self.figure.save(name, formats, dpi, background) if self.figure is not None else []
        if table:
            from hairline.export import strip_known_extension
            base = strip_known_extension(Path(name))
            path = base.with_name(f"{base.name}.csv")
            path.parent.mkdir(parents=True, exist_ok=True)
            self.table.to_csv(path, index=False)
            paths.append(path)
        return paths


def figure_for(endpoint: str, names: Sequence[str], what: str,
               draw: Callable[[], HairlineFigure | None]) -> HairlineFigure | None:
    """The endpoint's figure, or None with a warning when its `what` (groups, or a variable's categories) need more
    colours than the palette has: the table, values and text need none."""
    from hairline.settings import current_settings
    from hairline.slots import more_slots_advice
    settings = current_settings()

    def draw_advice(label: str, what: str) -> str:
        return more_slots_advice(label) if label.startswith("brand ") else f"fold small {what} into 'Other'"

    slots = len(settings.palette)
    if len(names) <= slots:
        return draw()
    warnings.warn(f"hairline: {endpoint}: {len(names)} {what} need more colours than the {slots} of "
                  f"{settings.palette_label}, so the result has no figure; its table, values and text are complete. "
                  f"To draw it, {draw_advice(settings.palette_label, what)}", UserWarning, stacklevel=3)
    return None
