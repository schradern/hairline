"""Shared helpers for the Python gallery scripts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import hairline as hl

GALLERY = Path(__file__).resolve().parents[1]
OUT = GALLERY / "out" / "python"
FRAME_KEYS = ["left", "right", "title_baselines", "subtitle_baselines", "legend_row_centers", "panels",
              "panel_header_baselines", "panel_header_lines", "y_title_left", "y_title_baseline", "x_title_baseline",
              "caption_baselines"]


def data(name: str) -> pd.DataFrame:
    return pd.read_csv(GALLERY / "data" / f"{name}.csv")


def finish(figure: hl.HairlineFigure, name: str) -> None:
    """Save PDF + PNG and the frame report used by the parity check."""
    hl.save(figure, OUT / name)
    report = figure.layout_report()
    (OUT / f"{name}.layout.json").write_text(json.dumps({key: report.get(key) for key in FRAME_KEYS}, indent=1))
