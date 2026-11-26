"""The descriptions of a systematic review's figures for their alt text: a funnel plot's studies, pooled estimate and
Egger's test as its header writes them, a PRISMA flow's records at each stage, and a risk-of-bias summary's overall
judgements and the domain most often judged high. Mirrored in R's review_alt.R."""

from __future__ import annotations

from collections.abc import Mapping

from hairline.alt_text import described, named
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


def risk_of_bias_description(spec: dict, locale: str) -> str:
    """'Risk-of-bias summary. Overall: 4 low, 3 some concerns, 1 high. Most often high: Randomisation (3).'; the
    overall row where the chart draws one, then the domains with the most high judgements where any has one."""
    def counts_text(index: int) -> str:
        low, some, high = (format_number(count, 0, locale) for count in spec["counts"][index])
        return word("rob_counts", locale, label=spec["domains"][index], low=low, some=some, high=high)
    overall = spec["overall"]
    findings = [counts_text(overall)] if overall is not None else []
    domains = [index for index in range(len(spec["domains"])) if index != overall]
    most = max(spec["counts"][index][2] for index in domains)
    if most > 0:
        names = [spec["domains"][index] for index in domains if spec["counts"][index][2] == most]
        findings.append(word("rob_most_high", locale, domains=named(names, locale), n=format_number(most, 0, locale)))
    return described("kind_risk_of_bias", " ".join(findings), locale)
