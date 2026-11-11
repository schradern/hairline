# Facets on a ridgeline: one panel per site on a shared age axis and one ridge height, each panel's n in its header,
# diagnoses by median age and a labelled reference line.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
ages <- gallery_data("ages")
ages$site <- ifelse(seq_len(nrow(ages)) %% 2 == 1, "Site North", "Site South")
plot <- hl_ridgeline(ages, "diagnosis", "age", facet = "site", show_n = TRUE, sort = "median",
                     reference = c(`65 years` = 65), x_title = "Age (years)",
                     title = "Age at admission by diagnosis at both sites",
                     subtitle = "540 ICU admissions, 2025; lines mark the medians", caption = "Synthetic data.")
finish(plot, "ridgeline_sites", "double")
