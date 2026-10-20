"""What every study endpoint returns: one computation, five views of it."""

from __future__ import annotations

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
