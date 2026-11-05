# A table for documents: the cohort's characteristics from hl_describe(), in hairline's typography.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
study <- suppressWarnings(hl_study(gallery_data("cohort"), group = "arm",
                                   variables = c("age", "sex", "sofa", "lactate"),
                                   labels = c(sofa = "SOFA score", lactate = "Lactate"),
                                   units = c(age = "years", sofa = "points", lactate = "mmol/l")))
plot <- hl_table(hl_describe(study)$table, "Characteristics by arm", subtitle = "Median (IQR) or n (%)",
                 footnotes = "IQR: interquartile range.", caption = "Synthetic data.", size = "double")
finish(plot, "table_characteristics", "double")
