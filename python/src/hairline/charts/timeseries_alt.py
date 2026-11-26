"""The description of a time series for its alt text: where each series' line starts, ends and is highest. The line
is the one the chart emphasises, the rolling mean (or with `summary=` the centre), not the raw values under it.
Mirrored in R's timeseries_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from hairline.alt_text import TIE_DIGITS, described
from hairline.charts.timeseries_summary import summary_series
from hairline.interactive import number_texts
from hairline.numbers import word
from hairline.tokens import load_tokens


def series_line(rows: pd.DataFrame, x: str, y: str, window: int, marks: tuple[str, str | None] | None) -> pd.DataFrame:
    """The drawn line of one series as `x` and `value`, in order of x, without its missing points."""
    if marks:
        found = summary_series(rows, x, y, *marks)
        line = pd.DataFrame({"x": found[x].to_numpy(), "value": found["centre"].to_numpy(dtype=float)})
    else:
        ordered = rows.sort_values(x, kind="mergesort")
        line = pd.DataFrame({"x": ordered[x].to_numpy(),
                             "value": ordered[y].rolling(int(window), min_periods=1).mean().to_numpy(dtype=float)})
    return line[line["x"].notna() & np.isfinite(line["value"])].reset_index(drop=True)


def moment_texts(values: pd.Series, locale: str) -> list[str]:
    """X values as the tooltips write them: ISO dates, with the clock time when any point has one (and its seconds
    when any has those); numbers by the shared digits rule."""
    if not pd.api.types.is_datetime64_any_dtype(values):
        return number_texts(values.to_numpy(dtype=float), False, locale=locale)
    moments = values.dt.round("s")
    seconds = bool((moments.dt.second != 0).any())
    timed = seconds or bool(((moments.dt.hour != 0) | (moments.dt.minute != 0)).any())
    shape = "%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M" if timed else "%Y-%m-%d"
    return list(moments.dt.strftime(shape))


def course(name: str, xs: list[str], values: list[str], line: pd.DataFrame, locale: str) -> str:
    """One series: from its first value to its last, and where it is highest (the earliest, on a tie): at its start,
    its end, or a point between, named."""
    suffix = "" if name else "_alone"
    if len(line) == 1:
        return word(f"line_point{suffix}", locale, name=name, value=values[0], when=xs[0])
    peak = int(np.argmax(np.round(line["value"].to_numpy(), TIE_DIGITS)))
    highest = word("peak_start", locale) if peak == 0 else word("peak_end", locale) if peak == len(line) - 1 else \
        word("peak_at", locale, peak=values[peak], when=xs[peak])
    return word(f"line_course{suffix}", locale, name=name, first=values[0], start=xs[0], last=values[-1],
                end=xs[-1], highest=highest)


def timeseries_description(lines: Sequence[tuple[str, pd.DataFrame]], percent: bool, locale: str) -> str:
    """'Line chart. ICU: from 41 (2025-01-01) to 52 (2025-12-01), highest 55 (2025-08-01). …' for the first
    `alt_text.max_series` series with points, then how many more; the values share one digits rule."""
    shown = [(name, line) for name, line in lines if len(line)]
    if not shown:
        return described("kind_lines", "", locale)
    every = pd.concat([line for _, line in shown], ignore_index=True)
    xs, values = moment_texts(every["x"], locale), number_texts(every["value"].to_numpy(), percent, locale=locale)
    most, sentences, start = load_tokens()["alt_text"]["max_series"], [], 0
    for name, line in shown:
        end = start + len(line)
        if len(sentences) < most:
            sentences.append(course(name, xs[start:end], values[start:end], line, locale))
        start = end
    left = len(shown) - len(sentences)
    if left:
        sentences.append(word("more_series_one", locale) if left == 1 else word("more_series_many", locale, n=left))
    return described("kind_lines", " ".join(sentences), locale)
