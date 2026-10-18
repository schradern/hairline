"""100 % stacked bars from raw rows: where patients went after the ICU, per unit, as shares."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
destinations = ["Home", "Rehabilitation", "Ward", "Care home", "Died"]
rows = data("destinations").sort_values("destination", key=lambda column: column.map(destinations.index),
                                         kind="stable")
figure = hl.bars(rows, "unit", by="destination", stacked=True, percent=True, horizontal=True,
                 order=["Surgical", "Medical", "Neurological", "Cardiac"], title="Destination after the ICU by unit",
                 subtitle="640 discharges, 2025", caption="Synthetic data.", size="double")
finish(figure, "bars_percent")
