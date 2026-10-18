# Venn diagram from membership columns: diabetes, hypertension and obesity among ICU patients.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_venn(gallery_data("comorbidities"), c("diabetes", "hypertension", "obesity"),
                title = "Diabetes, hypertension and obesity", subtitle = "600 ICU patients, 2025",
                caption = "Synthetic data.")
finish(plot, "venn_comorbidities", "double")
