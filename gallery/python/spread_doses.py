"""Spread rows for a skewed, discrete measure: doses on round levels with their shares, n per group, a group with
one case left out, implausible doses clipped off; the caption says what is not shown."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.spread(data("doses"), "procedure", "dose_mg", stats=("median", "levels", "n"), min_n=10, clip=0.99,
                   discrete=True, axis_title="Single dose (mg)", title="Doses by procedure",
                   subtitle="Range, interquartile range and median; the two most frequent doses",
                   caption="Synthetic data.", size="double")
finish(figure, "spread_doses")
