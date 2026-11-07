# Spread rows for a skewed, discrete measure: doses on round levels with their shares, n per group, a group with one
# case left out, implausible doses clipped off; the caption says what is not shown.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_spread(gallery_data("doses"), "procedure", "dose_mg", stats = c("median", "levels", "n"), min_n = 10,
                  clip = 0.99, discrete = TRUE, axis_title = "Single dose (mg)", title = "Doses by procedure",
                  subtitle = "Range, interquartile range and median; the two most frequent doses",
                  caption = "Synthetic data.")
finish(plot, "spread_doses", "double")
