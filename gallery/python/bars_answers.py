"""Rows with their own answers: each question's answers named inside its bar, in greys by position, the n of each
question in a column on the right."""

import hairline as hl

from common import data, finish

hl.use(brand=False)
figure = hl.bars(data("answers"), "question", "count", by="answer", stacked=True, percent=True, sort="given",
                 inside="name", show_n="column", title="Three short questions",
                 subtitle="Share of respondents answering each question", caption="Synthetic data.", size="double")
finish(figure, "bars_answers")
