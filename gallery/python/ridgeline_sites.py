"""Facets on a ridgeline: one panel per site on a shared age axis and one ridge height, each panel's n in its header,
diagnoses by median age and a labelled reference line."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
ages = data("ages")
ages["site"] = ["Site North" if index % 2 == 0 else "Site South" for index in range(len(ages))]
figure = hl.ridgeline(ages, "diagnosis", "age", facet="site", show_n=True, sort="median", reference={"65 years": 65},
                      x_title="Age (years)", title="Age at admission by diagnosis at both sites",
                      subtitle="540 ICU admissions, 2025; lines mark the medians", caption="Synthetic data.",
                      size="double")
finish(figure, "ridgeline_sites")
