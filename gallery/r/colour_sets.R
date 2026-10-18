# Every colour set as swatches: categorical palettes, purpose sets, sequential and diverging ramps.

library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_swatches(subtitle = "Palettes and purpose sets for groups, ramps for amounts",
                    caption = "hl_palettes() lists them; hl_use(palette = ) makes one the default.")
finish(plot, "colour_sets", "onehalf")
