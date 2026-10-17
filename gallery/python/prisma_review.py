"""PRISMA 2020 flow from the counts of a systematic review; counts that do not add up would give a warning."""

import hairline as hl

from common import finish

hl.use(brand=False)
counts = {"identified": 1240, "registers": 85, "duplicates": 260, "automation": 45, "screened": 1020,
          "excluded": 900, "sought": 120, "not_retrieved": 10, "assessed": 110,
          "excluded_reasons": {"Wrong population": 40, "Wrong intervention": 31, "No control group": 21},
          "included": 18, "reports": 22}
figure = hl.prisma(counts, subtitle="Systematic review of early mobilisation in the ICU",
                   caption="Synthetic counts.", size="double")
finish(figure, "prisma_review")
