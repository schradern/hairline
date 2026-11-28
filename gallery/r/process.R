# Process diagram in swimlanes: how a critical laboratory value reaches the physician, before and after a results
# system, the new steps highlighted and the open questions numbered.
library(hairline)
source(file.path("r", "common.R"))

hl_use(brand = FALSE)
plot <- hl_process(gallery_data("process_steps"), gallery_data("process_flows"), lane = "role", stage = "stage",
                   section = "version", status = "status", note = "note", label = "how",
                   title = "How a critical lab value reaches the physician",
                   subtitle = "Highlighted steps are new with the results system", caption = "Synthetic example.")
finish(plot, "process", "double")
