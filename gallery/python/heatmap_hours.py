"""Heatmap: the share of ICU beds occupied by hour of day across half a year, one cell per hour and week, its
colour blended along the ramp."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
hours = data("hours")
figure = hl.heatmap(hours, "hour", "week", "occupied", percent=True, gradient=True, x_title="Hour of day",
                    y_title="Week", z_title="Beds occupied", subtitle="Share of beds in use, by hour of day and week",
                    caption="Synthetic data.")
finish(figure, "heatmap_hours")
