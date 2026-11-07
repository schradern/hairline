"""Diverging bars for a rating scale: statements rated 1 to 10 in three sections, the ten levels in four bins, the
negatively worded statements recoded, median, IQR and n beside each row."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.likert(data("survey"), "statement", "rating", levels=range(1, 11), group="section",
                   reverse=["Waited too long on the day", "Had to repeat my details"],
                   title="Booking worked well; follow-up after the visit less so",
                   subtitle="Agreement with each statement, 1 (not at all) to 10 (completely)",
                   key_title="Rating", caption="Synthetic data.", size="double")
finish(figure, "likert_visits")
