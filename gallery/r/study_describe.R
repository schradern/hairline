# Study endpoint: describe a two-arm cohort once, then get Table 1 and its overview figure in one call.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
study <- suppressWarnings(hl_study(gallery_data("cohort"), group = "arm", time = "months", event = "died", id = "id",
                                   variables = c("age", "sex", "sofa", "lactate"),
                                   labels = c(sofa = "SOFA score", lactate = "Lactate (mmol/l)")))
result <- hl_describe(study)
figure <- result$figure + ggplot2::labs(caption = "Synthetic data.")
finish(figure, "study_describe", "double")
