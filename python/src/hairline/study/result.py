"""What every study endpoint returns: one computation, five views of it."""

from __future__ import annotations

import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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


def figure_for(endpoint: str, names: Sequence[str], what: str,
               draw: Callable[[], HairlineFigure | None]) -> HairlineFigure | None:
    """The endpoint's figure, or None with a warning when its `what` (groups, or a variable's categories) need more
    colours than the palette has: the table, values and text need none."""
    from hairline.settings import current_settings
    settings = current_settings()
    slots = len(settings.palette)
    if len(names) <= slots:
        return draw()
    warnings.warn(f"hairline: {endpoint}: {len(names)} {what} need more colours than the {slots} of "
                  f"{settings.palette_label}, so the result has no figure; its table, values and text are complete. "
                  f"Fold small {what} into 'Other' to draw it", UserWarning, stacklevel=3)
    return None
