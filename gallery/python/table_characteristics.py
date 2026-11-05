"""A table for documents: the cohort's characteristics from describe(), in hairline's typography."""

import warnings

import hairline as hl

from common import data, finish

hl.use(brand=False)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    study = hl.study(data("cohort"), group="arm", variables=["age", "sex", "sofa", "lactate"],
                     labels={"sofa": "SOFA score", "lactate": "Lactate"},
                     units={"age": "years", "sofa": "points", "lactate": "mmol/l"})
figure = hl.table(study.describe().table, "Characteristics by arm", subtitle="Median (IQR) or n (%)",
                  footnotes=["IQR: interquartile range."], caption="Synthetic data.", size="double")
finish(figure, "table_characteristics")
