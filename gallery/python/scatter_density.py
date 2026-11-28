"""Scatter density: 2,400 admissions counted in hexagons, with the linear fit on top."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
vitals = data("vitals").rename(columns={"systolic": "Systolic (mmHg)", "diastolic": "Diastolic (mmHg)"})
figure = hl.scatter(vitals, "Systolic (mmHg)", "Diastolic (mmHg)", density=True,
                    title="Diastolic pressure follows systolic pressure",
                    subtitle="Blood pressure at ICU admission, counted in hexagons", caption="Synthetic data.",
                    size="double")
finish(figure, "scatter_density")
