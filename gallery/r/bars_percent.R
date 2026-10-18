# 100 % stacked bars from raw rows: where patients went after the ICU, per unit, as shares.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
destinations <- c("Home", "Rehabilitation", "Ward", "Care home", "Died")
rows <- gallery_data("destinations")
rows <- rows[order(match(rows$destination, destinations)), ]
plot <- hl_bars(rows, "unit", by = "destination", stacked = TRUE, percent = TRUE, horizontal = TRUE,
                order = c("Surgical", "Medical", "Neurological", "Cardiac"),
                title = "Destination after the ICU by unit", subtitle = "640 discharges, 2025",
                caption = "Synthetic data.")
finish(plot, "bars_percent", "double")
