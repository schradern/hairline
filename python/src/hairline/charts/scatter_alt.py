"""The description of a scatter plot for its alt text: each panel's linear fit with the n, r and slope its header
writes, or with no fit, how many points it draws; with hexagons, the most points one holds. Mirrored in R's
scatter_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

from hairline.alt_text import described
from hairline.numbers import format_number, word
from hairline.tokens import load_tokens


def fit_text(stats: Sequence[tuple[str, str]], locale: str) -> str:
    """'n = 120, r = 0.62, slope 0.31' from a panel header's numbers (n, r and slope, as written)."""
    n, r, slope = (text for _, text in stats)
    return word("fit_stats", locale, n=n, r=r, slope=slope)


def fits_text(fits: Sequence[tuple[str | None, Sequence[tuple[str, str]]]], locale: str) -> str:
    """One fit on its own, or the first `alt_text.max_series` panels' fits by name and how many more."""
    if len(fits) == 1 and fits[0][0] is None:
        return word("fit_one", locale, stats=fit_text(fits[0][1], locale))
    most = load_tokens()["alt_text"]["max_series"]
    shown = "; ".join(word("fit_panel", locale, panel=panel, stats=fit_text(stats, locale))
                      for panel, stats in fits[:most])
    left = len(fits) - most
    more = [] if left <= 0 else [word("more_panels_one", locale) if left == 1 else
                                 word("more_panels_many", locale, n=left)]
    return " ".join([word("fit_panels", locale, fits=shown), *more])


def scatter_description(fits: Sequence[tuple[str | None, Sequence[tuple[str, str]]]], points: int,
                        locale: str, peak: int | None = None) -> str:
    """'Scatter plot. Linear fit: n = 120, r = 0.62, slope 0.31.' with a fit (per panel when faceted, the panel's
    name first), else 'Scatter plot. 120 points.'; with hexagons (`peak`, the most points in one), their kind and
    'Most points in one hexagon: 24.' after."""
    if fits:
        found = fits_text(fits, locale)
    else:
        found = word("points_one", locale) if points == 1 else \
            word("points_many", locale, n=format_number(points, 0, locale))
    if peak is None:
        return described("kind_scatter", found, locale)
    peaked = word("density_peak", locale, n=format_number(peak, 0, locale))
    return described("kind_scatter_density", f"{found} {peaked}", locale)
