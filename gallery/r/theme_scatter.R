# Single panel: scatter with three groups, axis titles, legend row and caption.
library(ggplot2)
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
points <- gallery_data("scatter")
points$group <- factor(points$group, levels = c("Low risk", "Medium risk", "High risk"))
plot <- ggplot(points, aes(sofa, lactate, colour = group)) + geom_point() +
  labs(title = "Lactate and SOFA score at admission", subtitle = "One dot per patient, three risk groups",
       caption = "Synthetic data. Lactate in mmol/l.", y = "Lactate", x = "SOFA score") +
  theme_hairline()
finish(plot, "theme_scatter", "double")
