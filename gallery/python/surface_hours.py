"""Surface: the share of ICU beds occupied by hour of day across half a year, turned to show the midday ridge."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
hours = data("hours")
figure = hl.surface(hours, "hour", "week", "occupied", percent=True, x_title="Hour of day", y_title="Week",
                    z_title="Beds occupied", subtitle="Share of beds in use, by hour of day and week",
                    caption="Synthetic data. Read exact values from a heatmap beside it.", size="double")
finish(figure, "surface_hours")
