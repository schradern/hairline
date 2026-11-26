"""Surface beside its heatmap: the share of ICU beds occupied by hour of day across half a year; the surface shows
the midday ridge, the heatmap the values, and in HTML a point marked in one is marked in the other."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
hours = data("hours")
figure = hl.surface(hours, "hour", "week", "occupied", percent=True, heatmap=True, x_title="Hour of day",
                    y_title="Week", z_title="Beds occupied", subtitle="Share of beds in use, by hour of day and week",
                    caption="Synthetic data.")
finish(figure, "surface_hours")
