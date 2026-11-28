"""Heatmap with marginal bars: bed occupancy by hour of day and week, each hour's and each week's mean beside the
grid."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
hours = data("hours")
figure = hl.heatmap(hours, "hour", "week", "occupied", percent=True, margins="mean", x_title="Hour of day",
                    y_title="Week", z_title="Beds occupied", title="Beds fill up by midday",
                    subtitle="Share of beds in use, by hour of day and week, with the mean of each",
                    caption="Synthetic data.")
finish(figure, "heatmap_margins")
