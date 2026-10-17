# PRISMA 2020 flow from the counts of a systematic review; counts that do not add up would give a warning.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
counts <- list(identified = 1240, registers = 85, duplicates = 260, automation = 45, screened = 1020, excluded = 900,
               sought = 120, not_retrieved = 10, assessed = 110,
               excluded_reasons = c("Wrong population" = 40, "Wrong intervention" = 31, "No control group" = 21),
               included = 18, reports = 22)
plot <- hl_prisma(counts, subtitle = "Systematic review of early mobilisation in the ICU", caption = "Synthetic counts.")
finish(plot, "prisma_review", "double")
