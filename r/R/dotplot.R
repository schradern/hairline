# Dot plot with intervals, mirroring the Python dotplot(): sorted by value, labels on the left,
# the value on the right; drawn with the forest plot's geometry.

#' Dot plot with intervals
#'
#' One dot per row, largest at the top. With `low` and `high` each dot gets
#' its interval and the numbers on the right; `reference` adds a vertical line.
#'
#' @param data A data frame.
#' @param label,estimate Columns: row label and value.
#' @param low,high Interval columns, optional.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param sort Sort by value, largest at the top.
#' @param ratio Values are ratios (log axis).
#' @param reference Value for a vertical reference line.
#' @param digits Decimals of the numbers.
#' @return A ggplot with the hairline frame.
#' @examples
#' rates <- data.frame(unit = c("Medical", "Surgical", "Cardiac"), mortality = c(0.13, 0.08, 0.06),
#'                     low = c(0.11, 0.07, 0.04), high = c(0.15, 0.10, 0.08))
#' hl_dotplot(rates, "unit", "mortality", "low", "high")
#' @export
hl_dotplot <- function(data, label, estimate, low = NULL, high = NULL, title = NULL, subtitle = NULL, caption = NULL,
                       sort = TRUE, ratio = FALSE, reference = NULL, digits = 2) {
  check_columns(data, c(label, estimate, low, high))
  interval <- !is.null(low) && !is.null(high)
  if (sort) data <- data[order(-data[[estimate]], seq_len(nrow(data))), , drop = FALSE]
  if (!interval) {
    data$.low <- data[[estimate]]
    data$.high <- data[[estimate]]
    low <- ".low"
    high <- ".high"
  }
  heading <- if (interval) paste(humanise(estimate), "[95 % CI]") else humanise(estimate)
  spec <- forest_spec(data, label, estimate, low, high, ratio = ratio, colour = lone_colour(),
                      study_heading = humanise(label), effect_heading = heading, digits = digits, marker = "dot",
                      interval = interval, null = reference)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(estimate), "by", gsub("_", " ", label)), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) forest_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
