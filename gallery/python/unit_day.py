"""Cause above effect on one time axis: the share of weekdays each place was occupied, the moves between places,
and below, the doctors and nurses needed at once, as steps on whole people."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.figure("Occupancy and staffing over the day", subtitle="Weekdays, January to July 2026",
                   caption="Synthetic data.", size="double", height_mm=190, panels=3, heights=(9, 3.5, 4.5),
                   sharex=True)
hours = {"Regular hours": (7, 16)}
hl.lanes(data("unit_stays"), "place", "start", "end", group="section", days="weekdays",
         flows=data("unit_moves"), spans=hours, into=figure, panel=0)
hl.levels(data("unit_staff"), "start", end="end", by="role", days="weekdays", into=figure, panel=1)
finish(figure, "unit_day")
