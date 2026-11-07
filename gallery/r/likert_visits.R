# Diverging bars for a rating scale: statements rated 1 to 10 in three sections, the ten levels in four bins, the
# negatively worded statements recoded, median, IQR and n beside each row.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_likert(gallery_data("survey"), "statement", "rating", levels = 1:10, group = "section",
                  reverse = c("Waited too long on the day", "Had to repeat my details"),
                  title = "Booking worked well; follow-up after the visit less so",
                  subtitle = "Agreement with each statement, 1 (not at all) to 10 (completely)",
                  key_title = "Rating", caption = "Synthetic data.")
finish(plot, "likert_visits", "double")
