"""Study endpoint: describe a two-arm cohort once, then get Table 1 and its overview figure in one call."""

import warnings

import hairline as hl

from common import data, finish

hl.use(brand=False)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    study = hl.study(data("cohort"), group="arm", time="months", event="died", id="id",
                     variables=["age", "sex", "sofa", "lactate"],
                     labels={"sofa": "SOFA score", "lactate": "Lactate (mmol/l)"})
result = study.describe()
result.figure.caption = "Synthetic data."
finish(result.figure, "study_describe")
