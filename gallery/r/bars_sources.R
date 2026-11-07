# Multiple choice: where patients found information and what they want more of, each answer as a share of
# respondents, the exclusive "none" answer drawn as context, each panel with its own n.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_bars(gallery_data("sources"), "answer", facet = "question", respondents = "respondent",
                context = "None of these", header = "n", scales = "shared", title = "Information before the visit",
                subtitle = "Share of respondents naming each answer", caption = "Synthetic data.", size = "double")
finish(plot, "bars_sources", "double")
