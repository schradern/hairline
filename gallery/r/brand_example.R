# The fictional example brand: readable brand colours, German number format.
library(ggplot2)
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = file.path(gallery_dir, "..", "brands", "example", "_brand.yml"))
points <- gallery_data("scatter")
points$group <- factor(points$group, levels = c("Low risk", "Medium risk", "High risk"))
plot <- ggplot(points, aes(sofa, lactate, colour = group)) + geom_point() +
  labs(title = "Lactate by risk group", subtitle = "Example University Hospital design", caption = "Synthetic data.",
       y = "Lactate", x = NULL) +
  theme_hairline()
finish(plot, "brand_example", "double")
