# Shared helpers for the R gallery scripts.

gallery_dir <- normalizePath(".")
out_dir <- file.path(gallery_dir, "out", "r")
frame_keys <- c("left", "right", "title_baselines", "subtitle_baselines", "legend_row_centers", "panels",
                "panel_header_baselines", "panel_header_lines", "y_title_left", "y_title_baseline",
                "x_title_baseline", "caption_baselines", "plot_boxes", "drawing_texts",
                "table_baselines", "table_value_xs", "header_run_xs")

gallery_data <- function(name) utils::read.csv(file.path(gallery_dir, "data", paste0(name, ".csv")))

finish <- function(plot, name, size) {
  hairline::hl_save(plot, file.path(out_dir, name), size = size)
  report <- hairline::hl_layout_report(plot, size = size)
  jsonlite::write_json(report[frame_keys], file.path(out_dir, paste0(name, ".layout.json")), auto_unbox = TRUE,
                       digits = NA, null = "null", pretty = TRUE)
}
