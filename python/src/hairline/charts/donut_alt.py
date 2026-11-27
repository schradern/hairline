"""The description of a donut or partition bars for its alt text: the total a donut's centre writes, then the largest
and smallest part of the top level with their shares as the labels write them. Mirrored in R's donut_alt.R."""

from __future__ import annotations

from hairline.alt_text import described, extremes
from hairline.numbers import word

# The words extremes() writes for slices: both ends, one slice alone, every slice the same.
SLICE_WORDS = ("slice_extremes", "slice_one", "slice_same")


def donut_description(ring: list[dict], total: str | None, total_label: str | None, locale: str,
                      kind: str = "kind_donut") -> str:
    """'Donut chart. Total: 700 patients. Largest: Home (59%); smallest: Died (3%).'; the total where the centre
    shows it, with the text under it; `kind` names partition bars, which show no total."""
    findings = [word("total_amount", locale, total=f"{total} {total_label}" if total_label else total)] if total \
        else []
    findings.append(extremes([(item["name"], item["share"], item["share_text"]) for item in ring], locale,
                             SLICE_WORDS))
    return described(kind, " ".join(findings), locale)
