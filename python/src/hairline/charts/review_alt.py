"""The descriptions of a systematic review's figures for their alt text: a funnel plot's studies, pooled estimate and
Egger's test as its header writes them, and a PRISMA flow's records at each stage. Mirrored in R's review_alt.R."""

from __future__ import annotations

from collections.abc import Mapping

from hairline.alt_text import described
from hairline.numbers import format_number, word


def funnel_description(studies: int, estimate: str, egger: str, locale: str) -> str:
    """'Funnel plot. 12 studies; pooled estimate 0.82, Egger's test p = 0.210.'"""
    found = word("funnel_found", locale, n=format_number(studies, 0, locale), estimate=estimate, egger=egger)
    return described("kind_funnel", found, locale)


# The stages the description names, each with the counts it adds together.
PRISMA_STAGES = (("prisma_identified", ("identified", "registers")), ("prisma_screened", ("screened",)),
                 ("prisma_assessed", ("assessed",)), ("prisma_included", ("included",)))


def prisma_description(counts: Mapping, locale: str) -> str:
    """'PRISMA flow diagram. 1,200 records identified, 800 screened, 40 reports assessed, 12 studies included.'; the
    records from registers count with those from databases, and stages left out of `counts` are left out here."""
    stages = [word(name, locale, n=format_number(sum(counts[key] for key in keys if key in counts), 0, locale))
              for name, keys in PRISMA_STAGES if keys[0] in counts]
    return described("kind_prisma", word("prisma_flow", locale, stages=", ".join(stages)), locale)
