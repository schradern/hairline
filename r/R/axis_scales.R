# Position scales with hairline's nice breaks and locale labels; applied by default to hairline plots.

decimals_for <- function(step) {
  digits <- max(0, -floor(log10(step) + 1e-9))
  while (abs(step * 10^digits - round(step * 10^digits)) > 1e-9 && digits < 10) digits <- digits + 1
  digits
}

axis_labels <- function(percent) {
  function(breaks) {
    values <- breaks[is.finite(breaks)]
    if (length(values) == 0) return(character())
    step <- if (length(values) > 1) values[2] - values[1] else 1
    digits <- decimals_for(step * if (percent) 100 else 1)
    top <- max(values)
    vapply(breaks, function(value) {
      if (!is.finite(value)) return(NA_character_)
      if (percent && isTRUE(all.equal(value, top))) return(hl_format_percent(value, digits))
      hl_format_number(if (percent) value * 100 else value, digits)
    }, character(1))
  }
}

hairline_position_scale <- function(aesthetic, percent, target, ...) {
  constructor <- if (aesthetic == "y") ggplot2::scale_y_continuous else ggplot2::scale_x_continuous
  resolved <- target %||% 5
  usable <- function(limits) length(limits) == 2 && all(is.finite(limits))
  breaks <- function(limits) if (usable(limits)) nice_breaks(limits[1], limits[2], resolved) else NULL
  limits <- function(limits) if (usable(limits)) axis_limits(limits[1], limits[2], breaks(limits)) else limits
  scale <- constructor(breaks = breaks, limits = limits, labels = axis_labels(percent),
                       expand = ggplot2::expansion(0, 0), ...)
  scale$hairline <- list(percent = percent, target_given = !is.null(target), arguments = list(...))
  scale
}

row_target <- function(rows) if (rows == 1) 5 else if (rows == 2) 4 else 3

#' Position scales with nice breaks
#'
#' Continuous position scales using hairline's 3–6 'nice' breaks, locale
#' number formatting and limits that end on a break. Applied automatically to
#' hairline plots; add explicitly to change `percent` or `target`.
#'
#' @param percent Treat values as shares and label them as percentages (unit on the top label only).
#' @param target Preferred number of breaks; `NULL` follows the panel rows (5, 4, then 3).
#' @param ... Passed to [ggplot2::scale_y_continuous()] or [ggplot2::scale_x_continuous()].
#' @return A ggplot2 scale.
#' @examples
#' shares <- data.frame(unit = c("A", "B", "C"), share = c(0.42, 0.65, 0.81))
#' ggplot2::ggplot(shares, ggplot2::aes(unit, share)) + ggplot2::geom_col() +
#'   ggplot2::labs(title = "Share of beds occupied") + theme_hairline() +
#'   scale_y_hairline(percent = TRUE)
#' @export
scale_y_hairline <- function(percent = FALSE, target = NULL, ...) hairline_position_scale("y", percent, target, ...)

#' @rdname scale_y_hairline
#' @export
scale_x_hairline <- function(percent = FALSE, target = NULL, ...) hairline_position_scale("x", percent, target, ...)

is_date_scale <- function(scale) inherits(scale, "ScaleContinuousDate") && !is.null(scale$range$range)

hairline_date_scale <- function() {
  breaks <- function(limits) if (length(limits) == 2 && all(is.finite(limits))) month_breaks(limits[1], limits[2])
  ggplot2::scale_x_date(breaks = breaks, labels = function(days) month_label(days), expand = ggplot2::expansion(0, 0))
}

is_plain_continuous <- function(scale) {
  inherits(scale, "ScaleContinuousPosition") && !inherits(scale, c("ScaleContinuousDate", "ScaleContinuousDatetime")) &&
    !is.null(scale$range$range)
}

auto_target_scale <- function(plot, built, rows) {
  scale <- plot@scales$get_scales("y")
  if (is.null(scale$hairline) || scale$hairline$target_given || row_target(rows) == 5) return(NULL)
  do.call(hairline_position_scale, c(list("y", scale$hairline$percent, row_target(rows)), scale$hairline$arguments))
}

default_position_scales <- function(plot, built) {
  rows <- max(built@layout$layout$ROW)
  scales <- list()
  if (!plot@scales$has_scale("y") && is_plain_continuous(built@layout$panel_scales_y[[1]])) {
    scales[[length(scales) + 1]] <- scale_y_hairline(target = row_target(rows))
  } else if (!is.null(replacement <- auto_target_scale(plot, built, rows))) {
    scales[[length(scales) + 1]] <- replacement
  }
  if (!plot@scales$has_scale("x") && is_plain_continuous(built@layout$panel_scales_x[[1]])) {
    scales[[length(scales) + 1]] <- scale_x_hairline(target = row_target(max(built@layout$layout$COL)))
  } else if (!plot@scales$has_scale("x") && is_date_scale(built@layout$panel_scales_x[[1]])) {
    scales[[length(scales) + 1]] <- hairline_date_scale()
  }
  scales
}
