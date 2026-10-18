"""What every study endpoint returns: one computation, four views of it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure


@dataclass
class Result:
    """`figure` (or None), `table` of formatted strings, `values` for inline use, and one sentence of `text`."""

    figure: HairlineFigure | None
    table: pd.DataFrame
    values: dict
    text: str

    def __repr__(self) -> str:
        return f"{self.text}\n\n{self.table.to_string(index=False)}"
