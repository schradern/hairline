# Facets with their own scale: cases per year for four procedures of very different size, the first and last year
# incomplete and drawn lighter.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_bars(gallery_data("procedures"), "year", "cases", facet = "procedure", sort = "given",
                partial = c("2021" = "2 months", "2026" = "10 months"), title = "Cases per year",
                subtitle = "By procedure, each panel on its own axis", caption = "Synthetic data.", size = "double")
finish(plot, "bars_facets", "double")
