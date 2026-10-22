"""PRISMA 2020 flow diagram from the counts of a systematic review."""

from __future__ import annotations

import math
import numbers
import warnings
from collections.abc import Mapping

from hairline.charts.prisma_geometry import prisma_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.numbers import format_number
from hairline.settings import current_settings

REMOVALS = (("duplicates", "Duplicate records"), ("automation", "Marked ineligible by automation tools"),
            ("other_removed", "Removed for other reasons"))


def counted(label: str, value: int) -> str:
    return f"{label} (n = {format_number(value, 0, current_settings().locale)})"


def number(value: int) -> str:
    return format_number(value, 0, current_settings().locale)


def check_counts(counts: Mapping) -> None:
    """Every count is a whole number of zero or more: records and reports cannot be negative or fractional."""
    reasons = counts.get("excluded_reasons", {})
    if not isinstance(reasons, Mapping):
        raise ValueError(f"hairline: prisma: excluded_reasons is {reasons!r}; give a mapping of reason to count, "
                         "such as {'Wrong population': 12}")
    named = [(key, value) for key, value in counts.items() if key != "excluded_reasons"]
    named += [(f"excluded_reasons[{reason!r}]", value) for reason, value in reasons.items()]
    for key, value in named:
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value) \
                or not value >= 0 or value != int(value):
            raise ValueError(f"hairline: prisma: {key} is {value!r}; counts must be whole numbers of 0 or more")


def check_sums(counts: Mapping) -> None:
    """Warn where the counts do not add up; reports and records can differ on purpose, so this is not an error."""
    removed = sum(counts.get(key, 0) for key, _ in REMOVALS)
    found = counts["identified"] + counts.get("registers", 0)
    checks = [("screened", found - removed, f"identified {number(found)} minus removed {number(removed)}")]
    after_screening = counts["screened"] - counts.get("excluded", 0)
    if "excluded" in counts:
        step = "sought" if "sought" in counts else "assessed"
        checks.append((step, after_screening, f"screened {number(counts['screened'])} minus excluded "
                                              f"{number(counts['excluded'])}"))
    if "sought" in counts and "assessed" in counts:
        lost = counts.get("not_retrieved", 0)
        checks.append(("assessed", counts["sought"] - lost,
                       f"sought {number(counts['sought'])} minus not retrieved {number(lost)}"))
    if "assessed" in counts and "excluded_reasons" in counts:
        reasons = sum(counts["excluded_reasons"].values())
        checks.append(("included", counts["assessed"] - reasons,
                       f"assessed {number(counts['assessed'])} minus excluded {number(reasons)}"))
    for key, expected, words in checks:
        if key in counts and counts[key] != expected:
            warnings.warn(f"hairline: prisma: {key} {number(counts[key])} is not {words}", UserWarning, stacklevel=3)


def prisma_rows(counts: Mapping) -> list[dict]:
    removed = [counted(label, counts[key]) for key, label in REMOVALS if key in counts]
    found = [counted("Records identified from databases", counts["identified"])]
    if "registers" in counts:
        found.append(counted("Records identified from registers", counts["registers"]))
    rows = [{"main": found, "exclusion": ["Records removed before screening:", *removed] if removed else None},
            {"main": [counted("Records screened", counts["screened"])],
             "exclusion": [counted("Records excluded", counts["excluded"])] if "excluded" in counts else None}]
    if "sought" in counts:
        rows.append({"main": [counted("Reports sought for retrieval", counts["sought"])],
                     "exclusion": [counted("Reports not retrieved", counts["not_retrieved"])]
                     if "not_retrieved" in counts else None})
    if "assessed" in counts:
        reasons = [counted(reason, value) for reason, value in counts.get("excluded_reasons", {}).items()]
        rows.append({"main": [counted("Reports assessed for eligibility", counts["assessed"])],
                     "exclusion": ["Reports excluded:", *reasons] if reasons else None})
    included = [counted("Studies included in review", counts["included"])]
    if "reports" in counts:
        included.append(counted("Reports of included studies", counts["reports"]))
    return rows + [{"main": included, "exclusion": None}]


def prisma_spec(counts: Mapping) -> dict:
    """Rows of main and exclusion boxes and the three phases, with every count formatted."""
    missing = [key for key in ("identified", "screened", "included") if key not in counts]
    if missing:
        raise ValueError(f"hairline: prisma needs identified, screened and included; missing {', '.join(missing)}")
    check_counts(counts)
    check_sums(counts)
    rows = prisma_rows(counts)
    return {"rows": rows, "phases": [("Identification", 0, 0), ("Screening", 1, len(rows) - 2),
                                     ("Included", len(rows) - 1, len(rows) - 1)]}


def prisma(counts: Mapping, *, title: str | None = None, subtitle: str | None = None, caption: str | None = None,
           size: str = "onehalf") -> HairlineFigure:
    """PRISMA 2020 flow: identified, screened, sought, assessed and included, with the exclusions beside them.

    `counts` keys: identified (and registers), duplicates, automation, other_removed, screened, excluded, sought,
    not_retrieved, assessed, excluded_reasons (reason -> n), included, reports."""
    spec = prisma_spec(counts)
    result = figure(title or "Study selection", subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: prisma_drawing(spec, box, measure, style))
    return fit_height(result)
