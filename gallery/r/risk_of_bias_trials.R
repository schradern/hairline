# Risk-of-bias summary from a wide table: one column per domain, judgements as written by reviewers.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
domains <- c("Randomisation", "Deviations", "Missing data", "Measurement", "Reporting")
plot <- hl_risk_of_bias(utils::read.csv(file.path(gallery_dir, "data", "bias.csv"), check.names = FALSE), "study",
                        domains = domains, subtitle = "Twelve trials, RoB 2 domains",
                        caption = "Synthetic data. Overall: each trial's worst domain.")
finish(plot, "risk_of_bias_trials", "double")
