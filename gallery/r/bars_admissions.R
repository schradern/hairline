# Bar chart from raw rows: admissions counted per diagnosis, women and men side by side.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_bars(gallery_data("admissions"), "diagnosis", by = "sex", subtitle = "Admissions to all ICUs, 2025",
                caption = "Synthetic data.")
finish(plot, "bars_admissions", "double")
