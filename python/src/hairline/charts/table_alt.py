"""The description of a table for its alt text: how many rows and columns and the columns' names; the HTML table
carries the cells themselves. Mirrored in R's table_alt.R."""

from __future__ import annotations

from hairline.alt_text import described, named
from hairline.charts.swimlanes_alt import counted
from hairline.numbers import word


def table_description(spec: dict, titled: bool, locale: str) -> str:
    """'Table. 5 rows and 4 columns: Group, n, Median and 1 more.'; without a title of its own the figure is titled
    "Table" already, so the kind is left out."""
    size = word("table_size", locale, rows=counted(len(spec["rows"]), "rows_one", "rows_many", locale),
                columns=counted(len(spec["header"]), "columns_one", "columns_many", locale),
                names=named(spec["header"], locale))
    return described("kind_table", size, locale) if titled else size
