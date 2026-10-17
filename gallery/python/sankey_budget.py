"""Sankey: household income through accounts into spending, links coloured by spending category."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.sankey(data("budget"), ["income", "account", "spending"], "euros", title="Where the household income goes",
                   subtitle="Monthly flows in euros", headings=["Income", "Account", "Spending"],
                   caption="Synthetic data.")
finish(figure, "sankey_budget")
