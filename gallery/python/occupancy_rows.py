"""The ICU occupancy report: two levels of detail per ward, key numbers, threshold, interim period."""

import pandas as pd

import hairline as hl

from common import data, finish

hl.use(brand=False)
occupancy = data("occupancy")
occupancy["date"] = pd.Timestamp("2025-01-01") + pd.to_timedelta(occupancy["day"], unit="D")
wards = ["Unit A", "Unit B", "Unit D"]
beds = occupancy.groupby("ward")["beds"].max()
figure = hl.timeseries(
    occupancy[occupancy["ward"].isin(wards)], x="date", y="share", by="ward", order=wards,
    title="ICU bed occupancy", subtitle="Share of beds occupied at 00:00 · 1 Jan 2025 – 30 Jun 2026",
    caption="Threshold for high load: 90 %. Synthetic data.", percent=True, threshold=0.9, threshold_label="90 %",
    threshold_legend="High-load threshold", stats=("mean", "median", "share_above"), share_label="Days ≥ 90%",
    key="share_above", key_panels=["Unit B"], highlight=["Unit B"],
    qualifiers={ward: f"{beds[ward]} beds" for ward in wards}, raw_label="Daily value", mean_label="7-day mean",
    bands=[{"start": "2025-05-01", "end": "2026-05-01", "label": "Interim, reduced beds",
            "panels": ["Unit B", "Unit D"]}],
    events=[{"x": "2025-05-01", "label": "Move out", "panels": ["Unit D"]},
            {"x": "2026-05-01", "label": "Move back", "panels": ["Unit D"]}], size="double")
finish(figure, "occupancy_rows")
