"""The groups profile() colours its tiles by, and the stacked bars every tile draws from them."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.colors import to_hex, to_rgb

from hairline.study.columns import infer_type, is_missing, level_text, levels
from hairline.tokens import load_tokens

if TYPE_CHECKING:
    from hairline.figure import HairlineFigure
    from hairline.study.model import Study

MISSING = "Missing"


@dataclass(frozen=True)
class Stratum:
    """A group's rows (a mask over the study's rows), or the whole cohort when `name` is None."""

    name: str | None
    mask: np.ndarray


def check_by(study: Study, by: str) -> None:
    """A column of the data holding a few groups; numbers and dates are refused with what to pass instead."""
    if by not in study.data.columns:
        raise ValueError(f"hairline: profile: by '{by}' is not a column of the data; columns: "
                         f"{', '.join(map(str, study.data.columns))}")
    kind = study.types.get(by) or infer_type(study.data[by])
    if kind != "categorical":
        raise ValueError(f"hairline: profile: by '{by}' holds {'dates' if kind == 'date' else 'numbers'}; colour by "
                         "a column of a few groups, such as sex or arm")
    study.require([by], "profile")


def strata(study: Study, by: str | None) -> list[Stratum]:
    """One stratum per group of `by` (the study's order for its own group), then the rows without one as
    'Missing'; without `by`, the whole cohort."""
    rows = len(study.data)
    if by is None:
        return [Stratum(None, np.ones(rows, dtype=bool))]
    check_by(study, by)
    column = study.data[by]
    present = ~is_missing(column)
    text = column.map(level_text).where(present)
    names = study.groups if by == study.group else levels(column)
    found = [Stratum(name, (text == name).to_numpy()) for name in names]
    rest = ~np.any([stratum.mask for stratum in found], axis=0) if found else np.ones(rows, dtype=bool)
    return found + ([Stratum(MISSING, rest)] if rest.any() else [])


def fill(color: str, surface: str) -> str:
    """The colour laid over the surface at the profile's opacity, as one opaque colour: the bars and their legend
    swatches read the same."""
    opacity = load_tokens()["profile"]["fill_opacity"]
    mixed = [opacity * top + (1 - opacity) * bottom for top, bottom in zip(to_rgb(color), to_rgb(surface),
                                                                          strict=True)]
    return to_hex(mixed)


def stack(result: HairlineFigure, index: int, colors: dict[str | None, str], parts: Sequence[tuple[Stratum,
          Sequence[float]]], places: dict, tip: Callable[[int, Stratum, float], str]) -> np.ndarray:
    """Each stratum's values on top of the ones before it, at `places` ({"spots", "sizes", "extents",
    "horizontal"}), a tooltip per non-empty segment; returns the totals. The bars stay out of the export's automatic
    bar tooltips, which could not name the bin, level or period."""
    ax, horizontal = result.axes[index], places["horizontal"]
    edge = {"edgecolor": result.settings.neutral["surface"], "linewidth": load_tokens()["bars"]["gap_pt"] / 2}
    base = np.zeros(len(places["spots"]))
    for stratum, values in parts:
        values = np.asarray(values, dtype=float)
        if horizontal:
            drawn = ax.barh(places["spots"], values, height=places["sizes"], left=base, color=colors[stratum.name],
                            **edge)
        else:
            drawn = ax.bar(places["spots"], values, width=places["sizes"], bottom=base, align="edge",
                           color=colors[stratum.name], **edge)
        ax.containers.remove(drawn)
        segment_targets(result, index, colors[stratum.name], stratum, values, base, places, tip)
        base = base + values
    return base


def segment_targets(result: HairlineFigure, index: int, color: str, stratum: Stratum, values: np.ndarray,
                    base: np.ndarray, places: dict, tip: Callable[[int, Stratum, float], str]) -> None:
    for spot, (value, low_end, (low, high)) in enumerate(zip(values, base, places["extents"], strict=True)):
        if value <= 0:
            continue
        top = low_end + value
        rect = (low_end, low, top, high) if places["horizontal"] else (low, low_end, high, top)
        at = (top, (low + high) / 2) if places["horizontal"] else ((low + high) / 2, top)
        result.target(index, stratum.name or places["series"], color, [{"rect": rect}],
                      [{"at": at, "text": tip(spot, stratum, float(value))}])
