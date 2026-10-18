# Chord diagram from raw rows: transfers between hospital units, both directions combined per pair.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_chord(gallery_data("transfers"), "origin", "destination", title = "Transfers between units",
                 subtitle = "500 transfers, 2025; ribbons take the colour of the first unit",
                 caption = "Synthetic data.")
finish(plot, "chord_transfers", "double")
