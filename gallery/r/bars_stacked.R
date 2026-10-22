# Stacked bars from raw rows: admissions per diagnosis, women and men stacked, totals at the ends.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_bars(gallery_data("admissions"), "diagnosis", by = "sex", stacked = TRUE, horizontal = FALSE,
                title = "Admissions by diagnosis and sex",
                subtitle = "Admissions to all ICUs, 2025", caption = "Synthetic data.", size = "double")
finish(plot, "bars_stacked", "double")
