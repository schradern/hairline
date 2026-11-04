"""Tables for documents: any frame of text or numbers in hairline's typography, numbers formatted in the locale,
exported by save() as PDF, PNG, SVG and as a real HTML table."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

import pandas as pd

from hairline.charts.table_geometry import table_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import auto_digits, format_number
from hairline.settings import current_settings

ALIGNS = ("left", "right", "center")
# A formatted number or percentage as text ("1 841", "−0,5", "12 %"): aligned as a number.
NUMBER_TEXT = re.compile(r"^[−-]?[\d\u202f\u00a0 .,]*\d(?:[\u202f\u00a0 ]?%)?$")


def column_texts(values: pd.Series, digits: int | None, locale: str) -> list[str]:
    """A column as text: numbers in the locale with the column's own decimals (counts whole), missing as a dash,
    text as it is."""
    if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
        numbers = values.to_numpy(dtype=float, na_value=float("nan"))
        places = auto_digits(numbers) if digits is None else digits
        return [format_number(value, places, locale) for value in numbers]
    return ["" if pd.isna(value) else str(value) for value in values]


def is_number_column(values: pd.Series) -> bool:
    """Numbers, or text that is a formatted number in every row (missing cells aside)."""
    if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
        return True
    present = [str(value) for value in values if not pd.isna(value) and str(value) not in ("", "–")]
    return bool(present) and all(NUMBER_TEXT.match(value) for value in present)


def column_aligns(data: pd.DataFrame, align: str | Sequence[str] | Mapping[str, str] | None) -> list[str]:
    """Numbers right, text left (the first column always left), unless `align` says otherwise: one alignment for
    every column, one per column, or a mapping of some columns."""
    found = ["right" if index and is_number_column(data[column]) else "left"
             for index, column in enumerate(data.columns)]
    if isinstance(align, str):
        found = [align] * len(found)
    elif isinstance(align, Mapping):
        unknown = [str(column) for column in align if column not in data.columns]
        if unknown:
            raise ValueError(f"hairline: table: align names {unknown[0]!r}, which is not a column; columns: "
                             f"{', '.join(map(str, data.columns))}")
        found = [align.get(column, default) for column, default in zip(data.columns, found, strict=True)]
    elif align is not None:
        if len(align) != len(found):
            raise ValueError(f"hairline: table: align gives {len(align)} alignments for {len(found)} columns")
        found = list(align)
    wrong = [value for value in found if value not in ALIGNS]
    if wrong:
        raise ValueError(f"hairline: table: align {wrong[0]!r} must be one of {', '.join(ALIGNS)}")
    return found


def bold_positions(data: pd.DataFrame, bold_rows: Sequence[int | str] | None) -> list[int]:
    """Rows to set in bold, by position (0 is the first body row) or by the text of their first column."""
    first, found = [str(value) for value in data.iloc[:, 0]], []
    for row in bold_rows or ():
        if isinstance(row, int) and not isinstance(row, bool):
            if not 0 <= row < len(data):
                raise ValueError(f"hairline: table: bold_rows names row {row}, but the table has {len(data)} rows")
            found.append(row)
        elif str(row) in first:
            found.append(first.index(str(row)))
        else:
            raise ValueError(f"hairline: table: bold_rows names {row!r}, which is neither a row position nor a value "
                             f"of the first column")
    return found


def table_spec(data: pd.DataFrame, *, digits: int | Mapping[str, int] | None = None,
               align: str | Sequence[str] | Mapping[str, str] | None = None,
               bold_rows: Sequence[int | str] | None = None) -> dict:
    if not isinstance(data, pd.DataFrame) or not len(data.columns):
        raise ValueError("hairline: table needs a data frame with at least one column")
    if not len(data):
        raise ValueError("hairline: table: the data has no rows to show")
    locale = current_settings().locale
    places = digits if isinstance(digits, Mapping) else {column: digits for column in data.columns}
    columns = [column_texts(data[column], places.get(column), locale) for column in data.columns]
    return {"header": [str(column) for column in data.columns], "rows": [list(row) for row in zip(*columns,
                                                                                                  strict=True)],
            "align": column_aligns(data, align), "bold": bold_positions(data, bold_rows)}


def table(data: pd.DataFrame, title: str | None = None, *, subtitle: str | None = None, caption: str | None = None,
          footnotes: Sequence[str] | None = None, bold_rows: Sequence[int | str] | None = None,
          align: str | Sequence[str] | Mapping[str, str] | None = None,
          digits: int | Mapping[str, int] | None = None, size: str = "onehalf") -> HairlineFigure:
    """A table in hairline's typography: a header row between hairline rules, numbers right-aligned in the locale
    (each column with its own decimals, or `digits`), text left-aligned; leading pairs of spaces indent a row
    (as in describe()'s table, which passes straight in). `bold_rows` (positions, or values of the first column)
    marks a chosen row; `footnotes` go under the table, each on its own line, before the caption. The first column
    wraps when the table is wider than the figure. `save()` writes it as PDF, PNG, SVG, and as an HTML table."""
    spec = table_spec(data, digits=digits, align=align, bold_rows=bold_rows)
    notes = "\n".join([*(footnotes or ()), *([caption] if caption else [])]) or None
    result = figure(title or "Table", subtitle=subtitle, caption=notes, size=size)
    result.draw(0, lambda box, measure, style: table_drawing(spec, box, measure, style))
    result.table_data = spec
    return fit_height(result)


def escaped(content: str) -> str:
    return content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def table_html(owner: HairlineFigure) -> str:
    """The table as one self-contained <figure> with a real <table>: a document tool that drops images or Markdown
    tables keeps it as a table, in hairline's font, sizes, inks and rules."""
    from hairline.interactive import font_faces
    from hairline.settings import role_size
    from hairline.tokens import load_tokens
    spec, settings, rules = owner.table_data, owner.settings, load_tokens()["table"]
    neutral, label = settings.neutral, role_size(settings, "label")
    rule_width = load_tokens()["lines"]["axis"] * settings.base_size

    def cell(tag: str, content: str, align: str, bold: bool = False) -> str:
        level, stripped = len(content) - len(content.lstrip(" ")), content.lstrip(" ")
        indent = f"padding-left:{level // 2 * settings.base_size:g}pt;" if level >= 2 and align == "left" else ""
        weight = f"font-weight:{rules['header_weight']};" if bold else ""
        return f'<{tag} style="text-align:{align};{indent}{weight}">{escaped(stripped)}</{tag}>'
    head = "".join(cell("th", content, align, True) for content, align in zip(spec["header"], spec["align"],
                                                                                strict=True))
    body = "".join("<tr>" + "".join(cell("td", content, align, index in spec["bold"])
                                    for content, align in zip(row, spec["align"], strict=True)) + "</tr>"
                   for index, row in enumerate(spec["rows"]))
    notes = "".join(f"<p>{escaped(line)}</p>" for line in (owner.caption or "").split("\n") if line)
    subtitle = f'<p class="hl-subtitle">{escaped(owner.subtitle)}</p>' if owner.subtitle else ""
    style = (f"{font_faces(settings.font)}"
             f".hl-table{{font-family:'{settings.font}',sans-serif;color:{neutral['ink']};margin:0}}"
             f".hl-table figcaption{{font-size:{role_size(settings, 'title'):g}pt;font-weight:600}}"
             f".hl-table .hl-subtitle{{font-size:{role_size(settings, 'subtitle'):g}pt;color:{neutral['muted']};"
             f"margin:0.2em 0 0.8em}}"
             f".hl-table table{{border-collapse:collapse;font-size:{label:g}pt;font-variant-numeric:tabular-nums}}"
             f".hl-table thead tr{{border-top:{rule_width:g}pt solid {neutral['axis']};"
             f"border-bottom:{rule_width:g}pt solid {neutral['axis']}}}"
             f".hl-table tbody tr:last-child{{border-bottom:{rule_width:g}pt solid {neutral['axis']}}}"
             f".hl-table th,.hl-table td{{padding:0.35em {rules['column_gap'] / 2 * settings.base_size:g}pt;"
             f"vertical-align:top}}"
             f".hl-table .hl-notes{{font-size:{role_size(settings, 'caption'):g}pt;color:{neutral['faint']}}}"
             f".hl-table .hl-notes p{{margin:0.3em 0}}")
    return (f'<figure class="hl-table"><style>{style}</style><figcaption>{escaped(owner.title)}</figcaption>'
            f'{subtitle}<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
            f'<div class="hl-notes">{notes}</div></figure>')
