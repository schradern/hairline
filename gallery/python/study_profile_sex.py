"""Study endpoint: the surgical cohort at a glance, every characteristic split by sex in the same colours."""

import warnings

import hairline as hl

from common import data, finish

hl.use(brand=False)
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    study = hl.study(data("surgery"), id="id", variables=["age", "height", "weight", "asa", "duration", "stay"],
                     labels={"asa": "ASA class", "duration": "Operating time", "stay": "Length of stay"},
                     units={"age": "years", "height": "cm", "weight": "kg", "duration": "minutes", "stay": "days"},
                     unit="patients")
result = study.profile(dates="surgery_date", by="sex")
result.figure.caption = "Synthetic data."
finish(result.figure, "study_profile_sex")
