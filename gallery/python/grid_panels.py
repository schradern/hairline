"""Grid of six panels, three columns, panel names only."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
occupancy = data("occupancy")
wards = list(dict.fromkeys(occupancy["ward"]))
figure = hl.figure("Occupancy by unit", subtitle="7-day mean, share of beds", caption="Synthetic data.",
                   size="double", panels=6, layout="grid", columns=3)
for index, ward in enumerate(wards):
    rows = occupancy[occupancy["ward"] == ward]
    figure.axes[index].plot(rows["day"], rows["mean7"], color=hl.palette()[0])
    figure.panel_header(index, ward)
finish(figure, "grid_panels")
