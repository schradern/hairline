#' Frame positions of a hairline plot
#'
#' Lays out the plot at the given size and returns the positions hairline
#' computes (pt from the top-left corner); the same keys as the Python
#' package's `layout_report()`, used for cross-language parity checks.
#'
#' @param plot A ggplot with [theme_hairline()].
#' @param width_mm,height_mm Figure size in mm; override the preset.
#' @param size Size preset, as in [hl_save()] (`NULL` for the plot's own); its base size applies unless one was set
#'   explicitly.
#' @return A named list.
#' @examples
#' plot <- ggplot2::ggplot(datasets::mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
#'   ggplot2::labs(title = "Fuel use by weight") + theme_hairline()
#' str(hl_layout_report(plot, size = "single")$panels)
#' @export
hl_layout_report <- function(plot, width_mm = NULL, height_mm = NULL, size = NULL) {
  framed <- frame_plan(plot, size, width_mm, height_mm, "hl_layout_report()")
  report_from_plan(framed$parts, framed$plan)
}

# The extracted parts and the planned frame of a plot at its saved size.
frame_plan <- function(plot, size, width_mm = NULL, height_mm = NULL, caller = "hairline") {
  size <- plot_size(plot, size)
  check_size_preset(size)
  plot <- plot_for_size(plot, size)
  size_mm <- fitted_size_mm(plot, figure_size_mm(size, width_mm, height_mm %||% plot@meta$hairline_height_mm))
  path <- tempfile(fileext = ".png")
  ragg::agg_png(path, width = size_mm[1], height = size_mm[2], units = "mm", res = 72)
  on.exit({
    grDevices::dev.off()
    unlink(path)
  })
  frame <- ggplot2::ggplotGrob(plot)
  if (!inherits(frame, "hairline_frame")) {
    stop(sprintf("hairline: %s needs a plot with + theme_hairline()", caller), call. = FALSE)
  }
  list(parts = frame$parts, plan = plan_frame(frame$parts, size_mm / 25.4 * 72))
}

report_from_plan <- function(parts, plan) {
  layout <- plan$layout
  title_style <- role_style(parts$settings, "title")
  report <- list(left = layout$left, right = layout$right, title_baselines = layout$title_baselines,
                 subtitle_baselines = layout$subtitle_baselines, legend_row_centers = layout$legend_row_centers,
                 panels = layout$panels[seq_along(parts$panels)],
                 panel_header_baselines = layout$panel_header_baselines,
                 panel_header_lines = vapply(seq_along(parts$panels), function(index) {
                   composed <- plan$composed[[as.character(index)]]
                   if (is.null(composed)) 0L else as.integer(composed$lines)
                 }, integer(1)),
                 y_title_left = layout$y_title_left, y_title_baseline = layout$y_title_baseline,
                 x_title_baseline = layout$x_title_baseline, x_title_row_baselines = layout$x_title_row_baselines,
                 caption_baselines = layout$caption_baselines,
                 title_line_rights = layout$left + vapply(plan$texts$title, text_width_pt, numeric(1),
                                                          style = title_style, USE.NAMES = FALSE),
                 legend_item_rights = vapply(plan$placed, `[[`, numeric(1), "right"),
                 legend_labels = vapply(plan$placed, `[[`, character(1), "label"), panel_letters = character(),
                 drawing_texts = drawing_texts(plan$shapes),
                 header_run_xs = unlist(lapply(plan$composed[order(as.integer(names(plan$composed)))],
                                               function(header) vapply(header$runs, `[[`, numeric(1), "x"))),
                 table_baselines = layout$table_baselines,
                 table_value_xs = table_value_xs(parts, plan),
                 bare_panels = if (parts$bare) seq_along(parts$panels) - 1L else integer(),
                 plot_boxes = lapply(layout$panels[seq_along(parts$panels)], fitted_box, aspect = parts$aspect))
  rapply(report, function(value) round(value, 2), classes = "numeric", how = "replace")
}
