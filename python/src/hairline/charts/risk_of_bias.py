"""Risk-of-bias summary: 100 % bars per domain with counts, an overall row, judgement colours."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from hairline.charts.common import check_columns
from hairline.charts.risk_of_bias_geometry import JUDGEMENTS, risk_of_bias_drawing
from hairline.figure import HairlineFigure, figure
from hairline.tokens import load_tokens

SYNONYMS = {"low": "low", "low risk": "low", "some": "some", "some concerns": "some", "unclear": "some",
            "moderate": "some", "high": "high", "high risk": "high", "serious": "high", "critical": "high"}


def judgement_of(value: object, study: object, domain: object) -> str:
    key = str(value).strip().lower()
    if key not in SYNONYMS:
        raise ValueError(f"hairline: risk of bias: judgement {value!r} for {study}, {domain} is not low, some concerns "
                         "or high")
    return SYNONYMS[key]


def long_table(data: pd.DataFrame, study: str, domain: str | None, judgement: str | None,
               domains: Sequence[str] | None) -> pd.DataFrame:
    if domains is not None:
        check_columns(data, [study, *domains])
        return data.melt(id_vars=[study], value_vars=list(domains), var_name="_domain", value_name="_judgement")
    check_columns(data, [study, domain, judgement])
    return data.rename(columns={domain: "_domain", judgement: "_judgement"})


def risk_of_bias_spec(data: pd.DataFrame, study: str, domain: str | None = None, judgement: str | None = None, *,
                      domains: Sequence[str] | None = None, overall: str | None = "Overall") -> dict:
    """Counts of low, some concerns and high per domain; the overall row takes each study's worst judgement."""
    table = long_table(data, study, domain, judgement, domains)
    table["_level"] = [judgement_of(value, row_study, row_domain) for value, row_study, row_domain in
                       zip(table["_judgement"], table[study], table["_domain"], strict=True)]
    names = list(dict.fromkeys(table["_domain"].astype(str)))
    counts = [[int(((table["_domain"].astype(str) == name) & (table["_level"] == level)).sum()) for level in JUDGEMENTS]
              for name in names]
    if overall:
        worst = table.groupby(study, sort=False)["_level"].agg(lambda levels: max(levels, key=JUDGEMENTS.index))
        names.append(overall)
        counts.append([int((worst == level).sum()) for level in JUDGEMENTS])
    return {"domains": names, "counts": counts, "overall": len(names) - 1 if overall else None,
            "colors": {level: load_tokens()["sets"]["judgement"][level] for level in JUDGEMENTS}}


def risk_of_bias(data: pd.DataFrame, study: str, domain: str | None = None, judgement: str | None = None, *,
                 domains: Sequence[str] | None = None, overall: str | None = "Overall", title: str | None = None,
                 subtitle: str | None = None, caption: str | None = None, size: str = "onehalf") -> HairlineFigure:
    """From a long table (study, domain, judgement) or a wide one (`domains` as columns)."""
    spec = risk_of_bias_spec(data, study, domain, judgement, domains=domains, overall=overall)
    result = figure(title or "Risk of bias", subtitle=subtitle, caption=caption, size=size)
    result.draw(0, lambda box, measure, style: risk_of_bias_drawing(spec, box, measure, style))
    labels = load_tokens()["risk_of_bias"]["labels"]
    result.legend([("square", spec["colors"][level], labels[level]) for level in JUDGEMENTS])
    return result
