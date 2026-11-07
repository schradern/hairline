"""Grid of six panels, three columns, panel names only."""

import pandas as pd

import hairline as hl

from common import data, finish

hl.use(brand=False)
occupancy = data("occupancy")
occupancy["date"] = pd.Timestamp("2025-01-01") + pd.to_timedelta(occupancy["day"], unit="D")
wards = list(dict.fromkeys(occupancy["ward"]))
figure = hl.figure("Occupancy by unit", subtitle="Share of beds occupied, 7-day mean, 2025 to mid-2026",
                   caption="Synthetic data.", size="double", panels=6, layout="grid", columns=3)
for index, ward in enumerate(wards):
    rows = occupancy[occupancy["ward"] == ward]
    figure.axes[index].plot(rows["date"], rows["mean7"], color=hl.palette()[0])
    figure.panel_header(index, ward)
    figure.percent_axis(index)
finish(figure, "grid_panels")
