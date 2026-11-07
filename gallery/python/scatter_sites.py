"""Facets on a scatter: one panel per site on shared axes, each with its own fit; ordered risk groups in one hue and
a labelled reference line, all options every chart shares."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
patients = data("scatter").rename(columns={"sofa": "SOFA score", "lactate": "Lactate (mmol/l)"})
patients["site"] = ["Site North" if index % 2 == 0 else "Site South" for index in range(len(patients))]
figure = hl.scatter(patients, "SOFA score", "Lactate (mmol/l)", by="group", facet="site",
                    order=["Low risk", "Medium risk", "High risk"], colors="oranges", key_title="Risk",
                    reference={"Upper normal": 2}, title="Lactate rises with the SOFA score at both sites",
                    subtitle="One dot per patient at admission", caption="Synthetic data.", size="double")
finish(figure, "scatter_sites")
