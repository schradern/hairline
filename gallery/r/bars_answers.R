# Rows with their own answers: each question's answers named inside its bar, in greys by position, the n of each
# question in a column on the right.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_bars(gallery_data("answers"), "question", "count", by = "answer", stacked = TRUE, percent = TRUE,
                sort = "given", inside = "name", show_n = "column", title = "Three short questions",
                subtitle = "Share of respondents answering each question", caption = "Synthetic data.",
                size = "double")
finish(plot, "bars_answers", "double")
