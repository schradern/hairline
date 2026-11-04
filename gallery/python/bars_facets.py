"""Facets with their own scale: cases per year for four procedures of very different size, the first and last year
incomplete and drawn lighter."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.bars(data("procedures"), "year", "cases", facet="procedure", sort="given",
                 partial={"2021": "2 months", "2026": "10 months"}, title="Cases per year",
                 subtitle="By procedure, each panel on its own axis", caption="Synthetic data.", size="double")
finish(figure, "bars_facets")
