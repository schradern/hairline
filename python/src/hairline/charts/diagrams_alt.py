"""The descriptions of the flow and set diagrams for their alt text: a Sankey's total and its largest flow at each
step, a chord diagram's largest exchange and the groups with the highest and lowest total, an arc diagram's largest
link, a Venn diagram's sets and how many are in all of them. Mirrored in R's diagrams_alt.R."""

from __future__ import annotations

from collections.abc import Sequence

from hairline.alt_text import CENTRE_WORDS, TIE_DIGITS, described, extremes, named
from hairline.numbers import auto_digits, format_number, word


def largest(entries: Sequence[tuple[str, float]], digits: int, locale: str) -> str:
    """'ICU → Ward (40)': the names with the largest value, ties named together, and that value."""
    high = max(round(value, TIE_DIGITS) for _, value in entries)
    tied = [(name, value) for name, value in entries if round(value, TIE_DIGITS) == high]
    return f"{named([name for name, _ in tied], locale)} ({format_number(tied[0][1], digits, locale)})"


def step_flows(links: Sequence[dict]) -> dict[int, dict[tuple[str, str], float]]:
    """Each step's flows from source to target, the colour groups added together, in order of first appearance."""
    steps: dict[int, dict[tuple[str, str], float]] = {}
    for link in links:
        flows = steps.setdefault(link["column"], {})
        key = (link["source"], link["target"])
        flows[key] = flows.get(key, 0.0) + link["value"]
    return steps


def sankey_description(spec: dict, locale: str) -> str:
    """'Sankey diagram. Total: 754. Largest flow per step: ICU → Ward (300); Ward → Home (280).'"""
    digits = auto_digits([link["value"] for link in spec["links"]])
    steps = step_flows(spec["links"])
    flows = [largest([(word("flow_name", locale, source=source, target=target), value)
                      for (source, target), value in steps[column].items()], digits, locale)
             for column in sorted(steps)]
    total = format_number(sum(node["value"] for node in spec["nodes"][0]), digits, locale)
    findings = [word("total_amount", locale, total=total),
                word("largest_flow" if len(flows) == 1 else "largest_flows", locale, flows="; ".join(flows))]
    return described("kind_sankey", " ".join(findings), locale)


def chord_description(spec: dict, locale: str) -> str:
    """'Chord diagram. Largest exchange: ICU and Ward (80). Highest total: ICU (120); lowest: Rehab (20).'"""
    digits = auto_digits([link["value"] for link in spec["links"]])
    pairs = [(word("pair_name", locale, first=link["source"], second=link["target"]), link["value"])
             for link in spec["links"]]
    nodes = [(node["name"], node["value"], node["value_text"]) for node in spec["nodes"]]
    findings = [word("largest_exchange", locale, pairs=largest(pairs, digits, locale)),
                extremes(nodes, locale, CENTRE_WORDS, centre=word("node_total", locale))]
    return described("kind_chord", " ".join(findings), locale)


def arcs_description(spec: dict, locale: str) -> str:
    """'Arc diagram. Largest link: ICU ↔ Ward (80).'; a link carrying both directions is named with both arrows."""
    digits = auto_digits([link["value"] for link in spec["links"]])
    pairs = [(link["pair"], link["value"]) for link in spec["links"]]
    return described("kind_arcs", word("largest_link", locale, pairs=largest(pairs, digits, locale)), locale)


def venn_description(spec: dict, locale: str) -> str:
    """'Venn diagram. Sets: Diabetes (120), Obesity (90). In both: 40.'; the last region holds every set."""
    sets = ", ".join(f"{entry['name']} ({entry['value_text']})" for entry in spec["sets"])
    overlap = word("venn_both" if len(spec["sets"]) == 2 else "venn_all", locale,
                   value=spec["regions"][-1]["value_text"])
    return described("kind_venn", f"{word('venn_sets', locale, sets=sets)} {overlap}", locale)


def process_description(spec: dict, locale: str) -> str:
    """'Process diagram. Lanes: Ward, Laboratory. Before: 5 steps, 4 flows. After: 6 steps, 6 flows. Highlighted:
    Portal.'; without sections the counts stand alone."""
    findings = [word("process_lanes", locale, lanes=named(spec["lanes"], locale))]
    for section in spec["sections"]:
        counts = {"steps": len(section["steps"]), "flows": len(section["flows"])}
        findings.append(word("process_section", locale, name=section["name"], **counts) if section["name"] is not None
                        else word("process_counts", locale, **counts))
    highlighted = list(dict.fromkeys(step["name"] for section in spec["sections"] for step in section["steps"]
                                     if step["status"] == "highlight"))
    if highlighted:
        findings.append(word("process_highlighted", locale, steps=named(highlighted, locale)))
    return described("kind_process", " ".join(findings), locale)
