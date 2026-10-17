# Funnel plot, mirroring the Python funnel(): effect against standard error with the error
# running down from 0, pseudo 95 % limits as a band, pooled line dashed, null line solid, Egger's test.

funnel_axes <- function(effects, errors, pooled, ratio) {
  reach <- hl_tokens()$funnel$z * max(errors)
  low <- min(effects, pooled - reach, 0)
  high <- max(effects, pooled + reach, 0)
  if (ratio) {
    breaks <- log_breaks(exp(low), exp(high), hl_tokens()$forest$max_ticks)
    labels <- vapply(breaks, function(value) hl_format_number(value, forest_decimals(value)), character(1))
    x_axis <- list(breaks = breaks, labels = labels, low = breaks[1], high = breaks[length(breaks)])
  } else {
    breaks <- nice_breaks(low, high)
    labels <- vapply(breaks, hl_format_number, character(1), digits = forest_decimals(breaks))
    x_axis <- list(breaks = breaks, labels = labels, low = min(low, breaks[1]),
                   high = max(high, breaks[length(breaks)]))
  }
  y_breaks <- nice_breaks(0, max(errors))
  y_axis <- list(breaks = y_breaks, labels = vapply(y_breaks, hl_format_number, character(1),
                                                    digits = forest_decimals(y_breaks)),
                 high = max(y_breaks[length(y_breaks)], max(errors)))
  list(x = x_axis, y = y_axis)
}

funnel_spec <- function(data, estimate, se, ratio = TRUE, pooled = NULL, x_title = NULL) {
  check_columns(data, c(estimate, se))
  effects <- if (ratio) log(data[[estimate]]) else data[[estimate]]
  errors <- data[[se]]
  weights <- 1 / errors^2
  centre <- if (is.null(pooled)) sum(weights * effects) / sum(weights) else if (ratio) log(pooled) else pooled
  axes <- funnel_axes(effects, errors, centre, ratio)
  list(points = lapply(seq_along(effects), function(index) c(effects[index], errors[index])), pooled = centre,
       ratio = ratio, null = 0, x_axis = axes$x, y_axis = axes$y, x_title = x_title %||% humanise(estimate),
       y_title = "Standard error", color = hl_settings()$palette[1], egger = egger_p(effects, errors))
}

funnel_area <- function(spec, box, measure, style) {
  spacing <- hl_tokens()$spacing
  base <- style$base
  line <- line_height(style, "label")
  widest <- max(vapply(unlist(spec$y_axis$labels), measure, numeric(1), role = "label"))
  c(box[1] + widest + spacing$y_labels_plot * base, box[2] + line + hl_tokens()$funnel$title_gap * base,
    box[1] + box[3], box[2] + box[4] - 2 * line - spacing$x_tick_pad * style$sizes$label - spacing$x_title * base)
}

funnel_scales <- function(spec, area) {
  transform <- if (isTRUE(spec$ratio)) log else identity
  low <- transform(spec$x_axis$low)
  high <- transform(spec$x_axis$high)
  list(x = function(value) area[1] + (value - low) / (high - low) * (area[3] - area[1]),
       y = function(value) area[2] + value / spec$y_axis$high * (area[4] - area[2]))
}
