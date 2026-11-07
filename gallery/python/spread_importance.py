"""Spread rows in sections: the rated usefulness of each feature of a patient portal, by area, the mean as an open
diamond beside the median, rows sorted by median."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.spread(data("importance"), "feature", "rating", section="area", panel_letters=True, color_by="area",
                   mean=True, sort="median", stats=("median", "iqr", "n"), discrete=True,
                   axis_title="Rated usefulness, 1 (not useful) to 10 (essential)",
                   title="What patients want from the portal", subtitle="Rated usefulness of each feature",
                   caption="Synthetic data.", size="double")
finish(figure, "spread_importance")
