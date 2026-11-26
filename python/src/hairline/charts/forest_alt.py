"""The description of a forest plot for its alt text: the pooled estimate with its interval where there is one, then
the rows with the highest and lowest estimate, in the plot's digits. Mirrored in R's forest_alt.R."""

from __future__ import annotations

from hairline.alt_text import described, extremes
from hairline.numbers import format_number, word


def forest_description(spec: dict, digits: int, locale: str) -> str:
    """'Forest plot. Pooled: 0.82 [0.70–0.96]. Highest: Lee 2021 (1.20); lowest: Smith 2019 (0.55).'"""
    pooled = spec["pooled"]
    findings = [word("forest_pooled", locale, label=pooled["label"], effect=pooled["effect_text"])] if pooled else []
    entries = [(row["study"], row["estimate"], format_number(row["estimate"], digits, locale)) for row in spec["rows"]]
    findings.append(extremes(entries, locale))
    return described("kind_forest", " ".join(finding for finding in findings if finding), locale)
