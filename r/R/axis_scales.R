# Position scales with hairline's nice breaks and locale labels; applied by default to hairline plots.

decimals_for <- function(step) {
  digits <- max(0, -floor(log10(step) + 1e-9))
  while (abs(step * 10^digits - round(step * 10^digits)) > 1e-9 && digits < 10) digits <- digits + 1
  digits
}

# Locale labels with the decimals the step needs; numbers from 10^9 on in one short-scale unit for the whole axis
# (0, 0.5 tn, 1 tn), so that thirteen digits never crowd an axis.
axis_labels <- function(percent) {
  function(breaks) {
    values <- breaks[is.finite(breaks)]
    if (length(values) == 0) return(character())
    step <- if (length(values) > 1) values[2] - values[1] else 1
    unit <- if (percent) NULL else number_unit(values)
    digits <- decimals_for(step * (if (percent) 100 else 1) / (unit$scale %||% 1))
    top <- max(values)
    vapply(breaks, function(value) {
      if (!is.finite(value)) return(NA_character_)
      if (percent && isTRUE(all.equal(value, top))) return(hl_format_percent(value, digits))
      if (percent) return(hl_format_number(value * 100, digits))
      format_compact(value, digits, unit)
    }, character(1))
  }
}

max_axis_digits <- 10

check_axis_digits <- function(digits) {
  is_whole <- is.numeric(digits) && length(digits) == 1 && !is.na(digits) && digits == round(digits)
  if (!is.null(digits) && !(is_whole && digits >= 0 && digits <= max_axis_digits)) {
    stop(sprintf("hairline: digits must be a whole number from 0 to %d, got %s", max_axis_digits,
                 paste(deparse(digits), collapse = "")), call. = FALSE)
  }
  digits
}

hairline_position_scale <- function(aesthetic, percent, target, digits, ..., margin = 0, whole = FALSE) {
  check_axis_digits(digits)
  constructor <- if (aesthetic == "y") ggplot2::scale_y_continuous else ggplot2::scale_x_continuous
  resolved <- target %||% 5
  usable <- function(limits) length(limits) == 2 && all(is.finite(limits))
  breaks <- function(limits) if (usable(limits)) nice_breaks(limits[1], limits[2], resolved, whole) else NULL
  limits <- function(limits) if (usable(limits)) axis_limits(limits[1], limits[2], breaks(limits), margin) else limits
  scale <- constructor(breaks = breaks, limits = limits, labels = axis_labels(percent),
                       expand = ggplot2::expansion(0, 0), ...)
  scale$hairline <- list(percent = percent, digits = digits, target_given = !is.null(target), target = target,
                         margin = margin, whole = whole, arguments = list(...))
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
#' @param digits Decimals of the values a reader looks up (tooltips of interactive output), so that 89.6 %
#'   never reads as 90 % next to a 90 % target; `NULL` follows the shared digits rule. Axis labels keep their own
#'   decimals, set by the step between breaks.
#' @param ... Passed to [ggplot2::scale_y_continuous()] or [ggplot2::scale_x_continuous()].
#' @return A ggplot2 scale.
#' @examples
#' shares <- data.frame(unit = c("A", "B", "C"), share = c(0.42, 0.65, 0.81))
#' ggplot2::ggplot(shares, ggplot2::aes(unit, share)) + ggplot2::geom_col() +
#'   ggplot2::labs(title = "Share of beds occupied") + theme_hairline() +
#'   scale_y_hairline(percent = TRUE)
#' @export
scale_y_hairline <- function(percent = FALSE, target = NULL, digits = NULL, ...) {
  hairline_position_scale("y", percent, target, digits, ...)
}

#' @rdname scale_y_hairline
#' @export
scale_x_hairline <- function(percent = FALSE, target = NULL, digits = NULL, ...) {
  hairline_position_scale("x", percent, target, digits, ...)
}

is_date_scale <- function(scale) inherits(scale, "ScaleContinuousDate") && !is.null(scale$range$range)

hairline_date_scale <- function() {
  breaks <- function(limits) if (length(limits) == 2 && all(is.finite(limits))) month_breaks(limits[1], limits[2])
  ggplot2::scale_x_date(breaks = breaks, labels = function(days) month_label(days), expand = ggplot2::expansion(0, 0))
}

is_plain_continuous <- function(scale) {
  inherits(scale, "ScaleContinuousPosition") && !inherits(scale, c("ScaleContinuousDate", "ScaleContinuousDatetime")) &&
    !is.null(scale$range$range)
}

# A hairline scale the plot already has, rebuilt with the panel grid's target (unless one was given) and the
# margin its marks need; NULL when it needs neither.
adjusted_scale <- function(plot, aesthetic, target, margin) {
  scale <- plot@scales$get_scales(aesthetic)
  if (is.null(scale$hairline$margin)) return(NULL)
  wanted <- if (scale$hairline$target_given) scale$hairline$target else target
  if (identical(wanted, scale$hairline$target %||% 5) && margin == scale$hairline$margin) return(NULL)
  do.call(hairline_position_scale, c(list(aesthetic, scale$hairline$percent, wanted, scale$hairline$digits),
                                     scale$hairline$arguments, list(margin = margin, whole = scale$hairline$whole)))
}

# The share of an axis the largest mark's half-size takes on the least plot height: points (their radius) and censor
# ticks (half their height). Data that close to an outer break widens the axis by it, so no mark is cut by the plot's
# edge. As Python's mark_margin().
mark_margin <- function(plot) {
  tokens <- hl_tokens()
  geoms <- lapply(plot@layers, function(layer) layer$geom)
  half <- max(c(0, if (any(vapply(geoms, inherits, logical(1), "GeomPoint"))) tokens$lines$point_radius,
                if (any(vapply(geoms, inherits, logical(1), "GeomCensorTick"))) tokens$survival$censor_tick / 2))
  half / tokens$spacing$min_plot_height
}

default_position_scales <- function(plot, built) {
  rows <- max(built@layout$layout$ROW)
  margin <- mark_margin(plot)
  scales <- Filter(Negate(is.null), list(wrapped_names_scale(plot, built)))
  if (!plot@scales$has_scale("y") && is_plain_continuous(built@layout$panel_scales_y[[1]])) {
    scales[[length(scales) + 1]] <- hairline_position_scale("y", FALSE, row_target(rows), NULL, margin = margin)
  } else if (!is.null(replacement <- adjusted_scale(plot, "y", row_target(rows), margin))) {
    scales[[length(scales) + 1]] <- replacement
  }
  columns <- fitting_target(plot, built, row_target(max(built@layout$layout$COL)), margin)
  if (!plot@scales$has_scale("x") && is_plain_continuous(built@layout$panel_scales_x[[1]])) {
    scales[[length(scales) + 1]] <- hairline_position_scale("x", FALSE, columns, NULL, margin = margin)
  } else if (!is.null(replacement <- adjusted_scale(plot, "x", columns, margin))) {
    scales[[length(scales) + 1]] <- replacement
  } else if (!plot@scales$has_scale("x") && is_date_scale(built@layout$panel_scales_x[[1]])) {
    scales[[length(scales) + 1]] <- hairline_date_scale()
  }
  scales
}

# A panel's plot width before the layout: the device's width less the margins, the gaps between columns and the y
# labels with their gap. As Python's estimated_plot_width().
estimated_plot_width <- function(built, settings) {
  spacing <- hl_tokens()$spacing
  base <- settings$base_size
  columns <- max(built@layout$layout$COL)
  usable <- grDevices::dev.size("in")[1] * 72 - 2 * spacing$margin * base
  column <- (usable - (columns - 1) * spacing$panel_columns * base) / columns
  labels <- tryCatch(as.character(built@layout$panel_params[[1]]$y$get_labels()), error = function(error) character())
  labels <- labels[!is.na(labels)]
  style <- role_style(settings, "label")
  widest <- if (length(labels)) max(vapply(labels, text_width_pt, numeric(1), style = style)) else 0
  column - if (widest > 0) widest + spacing$y_labels_plot * base else 0
}

# Whether neighbouring x labels keep `ticks.label_rows_gap` between them: each centred on its break, or aligned
# inward at the plot's edges, as they are drawn. As Python's labels_fit().
labels_fit <- function(breaks, labels, limits, width, settings) {
  style <- role_style(settings, "label")
  gap <- hl_tokens()$ticks$label_rows_gap * style$size
  offsets <- (breaks - limits[1]) / diff(limits)
  sizes <- vapply(labels, text_width_pt, numeric(1), style = style)
  starts <- offsets * width - sizes * edge_hjust(offsets)
  all(utils::head(starts, -1) + utils::head(sizes, -1) + gap <= starts[-1] + 1e-9)
}

# The largest tick target for the x axis, from the panel grid's down to three, whose labels stand apart on the plot's
# estimated width. As Python's fitting_target().
fitting_target <- function(plot, built, target, margin) {
  scale <- built@layout$panel_scales_x[[1]]
  range <- if (is_plain_continuous(scale)) scale$range$range else NULL
  if (is.null(range) || !all(is.finite(range)) || grDevices::dev.cur() == 1) return(target)
  given <- plot@scales$get_scales("x")$hairline
  if (!is.null(given) && is.null(given$margin)) return(target)
  settings <- plot@meta$hairline_settings %||% hl_settings()
  width <- estimated_plot_width(built, settings)
  percent <- isTRUE(given$percent)
  whole <- isTRUE(given$whole)
  for (candidate in seq(target, 3)) {
    breaks <- nice_breaks(range[1], range[2], candidate, whole)
    labels <- axis_labels(percent)(breaks)
    if (labels_fit(breaks, labels, axis_limits(range[1], range[2], breaks, margin), width, settings)) {
      return(candidate)
    }
  }
  3
}

# Names on an x axis, each wrapped to its slot (the plot's estimated width over the axis range, less the label gap),
# so neighbours never meet; NULL when they already fit on one line. A word wider than its slot cannot be placed: the
# plot is refused with what would fit. As Python's wrapped_names().
wrapped_names_scale <- function(plot, built) {
  params <- built@layout$panel_params[[1]]$x
  if (is.null(params) || grDevices::dev.cur() == 1 || !plot@scales$has_scale("x")) return(NULL)
  labels <- tryCatch(as.character(params$get_labels()), error = function(error) character())
  if (!length(labels) || !any(grepl("[[:alpha:]]", labels)) || inherits(params$scale, "ScaleContinuousDate")) {
    return(NULL)
  }
  settings <- plot@meta$hairline_settings %||% hl_settings()
  style <- role_style(settings, "label")
  span <- diff(range(params$continuous_range))
  gap <- hl_tokens()$ticks$label_rows_gap * style$size
  slot <- estimated_plot_width(built, settings) / span - gap
  lines <- lapply(gsub("\n", " ", labels, fixed = TRUE), wrap_text, style = style, max_width = slot)
  widest <- max(vapply(unlist(lines), text_width_pt, numeric(1), style = style))
  if (widest > slot + 1e-6) {
    stop(sprintf(paste0("hairline: the %d names on the x axis do not fit side by side: a word needs %.0f pt and each ",
                        "name has %.0f pt; use a wider size, fewer groups, or a chart that lists the groups as rows ",
                        "(bars, spread, ridgeline, dotplot)"), length(labels), widest, max(slot, 0)), call. = FALSE)
  }
  wrapped <- vapply(lines, paste, character(1), collapse = "\n")
  if (identical(wrapped, labels)) return(NULL)
  scale <- plot@scales$get_scales("x")$clone()
  scale$labels <- wrapped
  scale
}
