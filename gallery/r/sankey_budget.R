# Sankey: household income through accounts into spending, links coloured by spending category.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_sankey(gallery_data("budget"), c("income", "account", "spending"), "euros",
                  title = "Where the household income goes", subtitle = "Monthly flows in euros",
                  headings = c("Income", "Account", "Spending"), caption = "Synthetic data.")
finish(plot, "sankey_budget", "double")
