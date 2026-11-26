"""The description of a correlation heatmap for its alt text: the pairs with the highest and lowest correlation, as
their cells write them. Mirrored in R's correlation_alt.R."""

from __future__ import annotations

from hairline.alt_text import described, extremes
from hairline.numbers import word


def correlation_description(spec: dict, locale: str) -> str:
    """'Correlation matrix. Highest: Age and SOFA (0.62); lowest: Age and GCS (−0.41).' over the lower triangle's
    pairs, reading row by row, the earlier column named first."""
    names, matrix, texts = spec["names"], spec["matrix"], spec["texts"]
    entries = [(word("pair_name", locale, first=names[column], second=names[row]), float(matrix[row][column]),
                texts[row][column]) for row in range(len(names)) for column in range(row)]
    return described("kind_correlation", extremes(entries, locale), locale)
