# Study endpoint: the surgical cohort at a glance, every characteristic split by sex in the same colours.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
study <- suppressWarnings(hl_study(gallery_data("surgery"), id = "id",
                                   variables = c("age", "height", "weight", "asa", "duration", "stay"),
                                   labels = c(asa = "ASA class", duration = "Operating time", stay = "Length of stay"),
                                   units = c(age = "years", height = "cm", weight = "kg", duration = "minutes",
                                             stay = "days"),
                                   unit = "patients"))
result <- hl_profile(study, dates = "surgery_date", by = "sex")
figure <- result$figure + ggplot2::labs(caption = "Synthetic data.")
finish(figure, "study_profile_sex", "double")
