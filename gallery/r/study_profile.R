# Study endpoint: one surgical cohort at a glance, each characteristic in a tile of its own.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
study <- suppressWarnings(hl_study(gallery_data("surgery"), id = "id",
                                   variables = c("age", "sex", "height", "weight", "asa", "duration", "stay"),
                                   labels = c(asa = "ASA class", duration = "Operating time", stay = "Length of stay"),
                                   units = c(age = "years", height = "cm", weight = "kg", duration = "minutes",
                                             stay = "days"),
                                   unit = "patients"))
result <- hl_profile(study, dates = "surgery_date")
figure <- result$figure + ggplot2::labs(caption = "Synthetic data.")
finish(figure, "study_profile", "double")
