# Spread rows with written columns: operating time drawn per ASA class, age and length of stay beside it.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_spread(gallery_data("surgery"), "asa", "duration", stats = c("median", "iqr", "n"),
                  order = c("ASA I", "ASA II", "ASA III", "ASA IV"),
                  columns = c(age = "Age (years)", stay = "Stay (days)"), axis_title = "Minutes",
                  title = "Operating time by ASA class", subtitle = "Elective operations, 2022 to 2024",
                  caption = "Synthetic data.")
finish(plot, "spread_columns", "double")
