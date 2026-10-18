"""Run the gallery in Python and R and compare the frame positions each language computed.

Every layout key must have the same shape in both reports and every position must agree within 1 pt.
Exit status 0 means parity; otherwise a table lists figure, key, Python value and R value.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GALLERY = REPO / "gallery"
FIGURES = ["theme_scatter", "occupancy_rows", "grid_panels", "brand_example", "donut_discharge", "donut_nested",
           "partition_discharge", "km_trial", "forest_meta", "raincloud_stay",
           "sankey_budget",
           "bars_admissions", "dotplot_rates", "scatter_fit",
           "correlation_patients", "funnel_trials",
           "risk_of_bias_trials", "prisma_review",
           "arcs_pathways", "ridgeline_ages", "bars_stacked", "bars_percent", "chord_transfers",
           "venn_comorbidities", "study_describe", "spread_occupancy"]
TOLERANCE_PT = 1.0


def run_gallery() -> None:
    environment = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}
    python = REPO / "python" / ".venv" / "bin" / "python"
    for name in FIGURES:
        subprocess.run([str(python), f"{name}.py"], cwd=GALLERY / "python", check=True)
        subprocess.run(["Rscript", f"r/{name}.R"], cwd=GALLERY, check=True, env=environment,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def flatten(value: object) -> list[float]:
    if isinstance(value, list):
        return [number for item in value for number in flatten(item)]
    return [] if value is None else [float(value)]


def compare(name: str) -> list[tuple[str, str, str, str]]:
    python = json.loads((GALLERY / "out" / "python" / f"{name}.layout.json").read_text())
    r = json.loads((GALLERY / "out" / "r" / f"{name}.layout.json").read_text())
    problems = []
    for key, expected in python.items():
        left, right = flatten(expected), flatten(r.get(key))
        if len(left) != len(right):
            problems.append((name, key, str(left), str(right)))
        elif any(abs(a - b) > TOLERANCE_PT for a, b in zip(left, right, strict=True)):
            problems.append((name, key, str([round(a, 1) for a in left]), str([round(b, 1) for b in right])))
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-run", action="store_true", help="compare existing reports without re-running")
    if not parser.parse_args().no_run:
        run_gallery()
    problems = [problem for name in FIGURES for problem in compare(name)]
    for figure, key, python, r in problems:
        sys.stderr.write(f"{figure:<16} {key:<24} python {python}\n{'':<41} r      {r}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
