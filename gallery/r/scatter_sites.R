# Facets on a scatter: one panel per site on shared axes, each with its own fit; ordered risk groups in one hue and
# a labelled reference line, all options every chart shares.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
patients <- gallery_data("scatter")
names(patients)[match(c("sofa", "lactate"), names(patients))] <- c("SOFA score", "Lactate (mmol/l)")
patients$site <- ifelse(seq_len(nrow(patients)) %% 2 == 1, "Site North", "Site South")
plot <- hl_scatter(patients, "SOFA score", "Lactate (mmol/l)", by = "group", facet = "site",
                   order = c("Low risk", "Medium risk", "High risk"), colors = "oranges", key_title = "Risk",
                   reference = c(`Upper normal` = 2), title = "Lactate rises with the SOFA score at both sites",
                   subtitle = "One dot per patient at admission", caption = "Synthetic data.")
finish(plot, "scatter_sites", "double")
