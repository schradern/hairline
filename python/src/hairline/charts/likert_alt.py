"""The description of a Likert chart for its alt text: the items with the highest and lowest share of ratings on
the high side of the split, those levels named as the key names them. Mirrored in R's likert_alt.R."""

from __future__ import annotations

from hairline.alt_text import described, extremes, percent_text
from hairline.charts.distribution_alt import FACET_PARTS

# The words extremes() writes for the items: both ends, one item alone, every item the same; the levels as a field.
ITEM_WORDS = ("likert_extremes", "likert_one", "likert_same")


def high_levels(bins: list[dict]) -> list[float]:
    """The levels on the high side of the split, low to high."""
    return sorted(level for entry in bins if entry["side"] == "right" for level in entry["levels"])


def likert_description(spec: dict, levels: str, faceted: bool, locale: str) -> str:
    """'Likert chart. Highest share at 4–5: Staffing (72%); lowest: Parking (18%).' over the rows as drawn, each
    named with its block where faceted ("2025 · Staffing"); `levels` names the high side as the key does."""
    entries = []
    for row in spec["rows"]:
        share = sum(value for value, entry in zip(row["shares"], spec["bins"], strict=True) if entry["side"] == "right")
        name = f"{row['section']}{FACET_PARTS}{row['name']}" if faceted else row["name"]
        entries.append((name, share, percent_text(share, 0, locale)))
    return described("kind_likert", extremes(entries, locale, ITEM_WORDS, levels=levels), locale)
