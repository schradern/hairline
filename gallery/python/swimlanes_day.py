"""One real day: which patient is where, the theatre time as a darker band, then the doctors' tasks given to the
first free doctor."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
stays = data("unit_stays")
day = stays[stays["day"] == "2026-01-07"]
doctors = day[day["section"] != "Recovery"].assign(role="Doctors")
figure = hl.figure("One day in the unit", subtitle="7 January 2026: places, then the doctors' tasks",
                   caption="Synthetic data.", size="double", height_mm=150, panels=2, heights=(9, 3), sharex=True)
hl.swimlanes(day, "place", "start", "end", label="patient", group="section", into=figure, panel=0)
hl.swimlanes(doctors, None, "start", "end", label="patient", group="role", assign="first_free",
             color_by="section", into=figure, panel=1)
finish(figure, "swimlanes_day")
