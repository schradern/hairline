# A binned colour key in the legend row (the R twin of the Python package's HairlineFigure.legend_ramp()): its title,
# then one small outlined square per step, right-aligned beside the series items.

hairline_ramp_key <- S7::new_class("hairline_ramp_key", package = "hairline", properties = list(key = S7::class_any))

# The key's title, step labels and colours. Colours given one per step are the bins themselves (lanes, levels); a ramp
# is read at each step.
ramp_key <- function(ramp = NULL, steps = NULL, title = NULL, format = "percent", limits = c(0, 1), digits = NULL) {
  if (!format %in% c("percent", "number")) {
    stop(sprintf("hairline: legend_ramp: format '%s' must be 'percent' or 'number'", format), call. = FALSE)
  }
  named <- is.null(ramp) || (is.character(ramp) && length(ramp) == 1 && !is_hex(ramp))
  colours <- if (named) hl_ramp(ramp) else as.character(ramp)
  steps <- as.numeric(steps %||% unlist(hl_tokens()$legend_ramp$steps))
  if (!(length(limits) == 2 && limits[2] > limits[1])) {
    stop(sprintf("hairline: legend_ramp: limits need low below high; got %s", paste(format(limits), collapse = ", ")),
         call. = FALSE)
  }
  outside <- steps[steps < limits[1] | steps > limits[2]]
  if (length(outside)) {
    stop(sprintf("hairline: legend_ramp: step %s lies outside the limits %s to %s", format(outside[1]),
                 format(limits[1]), format(limits[2])), call. = FALSE)
  }
  binned <- !named && length(colours) == length(steps)
  labels <- vapply(steps, function(step) {
    places <- digits %||% exact_places(step * if (format == "percent") 100 else 1)
    if (format == "percent") hl_format_percent(step, places) else hl_format_number(step, places)
  }, character(1))
  picked <- if (binned) colours else
    colours[round((steps - limits[1]) / (limits[2] - limits[1]) * (length(colours) - 1)) + 1]
  list(title = title, labels = labels, colors = picked)
}

#' Binned colour key
#'
#' A key for colours that stand for amounts: its title, then one small square
#' per step with a hairline outline (so the lightest step stays visible on the
#' surface), right-aligned in the legend row beside the series items. Charts
#' with a ramp ([hl_lanes()], [hl_levels()], [hl_correlation()]) add it
#' themselves.
#'
#' @param ramp A ramp name, or its colours; colours given one per step are the bins themselves.
#' @param steps Values within `limits`; by default 25 %, 50 %, 75 % and 100 % of a share.
#' @param title Title before the squares, e.g. `"Share of days"`.
#' @param format `"percent"` or `"number"`.
#' @param limits The range the ramp spans.
#' @param digits Decimals of the step labels; by default as many as each step needs.
#' @return An object to add to a ggplot with `+`.
#' @examples
#' ggplot2::ggplot(datasets::faithful, ggplot2::aes(eruptions, waiting)) + ggplot2::geom_point() +
#'   ggplot2::labs(title = "Old Faithful") + theme_hairline() + hl_legend_ramp("blue", title = "Share")
#' @export
hl_legend_ramp <- function(ramp = NULL, steps = NULL, title = NULL, format = "percent", limits = c(0, 1),
                           digits = NULL) {
  hairline_ramp_key(key = ramp_key(ramp, steps, title, format, limits, digits))
}

add_hairline_ramp_key <- function(object, plot, ...) {
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  plot@meta$hairline_ramp_key <- object@key
  plot
}
