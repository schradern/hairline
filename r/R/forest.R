# Forest plot: a results table with intervals, weighted squares and a pooled diamond;
# mirrors the Python forest().

forest_decimals <- function(values) {
  for (digits in 0:3) if (all(abs(round(values, digits) - values) < 1e-9)) return(digits)
  3
}

forest_axis <- function(lows, highs, ratio) {
  null <- if (ratio) 1 else 0
  low <- min(c(lows, null))
  high <- max(c(highs, null))
  breaks <- if (ratio) log_breaks(low, high, hl_tokens()$forest$max_ticks) else nice_breaks(low, high)
  limits <- if (ratio) range(breaks) else axis_limits(low, high, breaks)
  shared <- forest_decimals(breaks)
  labels <- vapply(breaks, function(value) hl_format_number(value, if (ratio) forest_decimals(value) else shared),
                   character(1))
  list(breaks = breaks, labels = labels, low = limits[1], high = limits[2])
}

forest_check_rows <- function(data, study, low, high, ratio) {
  for (index in seq_len(nrow(data))) {
    if (data[[low]][index] > data[[high]][index]) {
      stop(sprintf("hairline: forest: '%s' has a lower limit above its upper limit", data[[study]][index]),
           call. = FALSE)
    }
    if (ratio && data[[low]][index] <= 0) {
      stop(sprintf("hairline: forest: '%s' has a limit of 0 or below on a ratio scale; pass ratio = FALSE for %s",
                   data[[study]][index], "differences"), call. = FALSE)
    }
  }
}

forest_rows <- function(data, study, estimate, low, high, weight, columns, digits) {
  total <- if (is.null(weight)) NULL else sum(data[[weight]])
  lapply(seq_len(nrow(data)), function(index) {
    row <- data[index, , drop = FALSE]
    list(study = as.character(row[[study]]), estimate = row[[estimate]], low = row[[low]], high = row[[high]],
         weight = if (is.null(weight)) NULL else row[[weight]],
         cells = lapply(unname(columns), function(column) as.character(row[[column]])),
         effect_text = hl_format_interval(row[[estimate]], row[[low]], row[[high]], digits),
         weight_text = if (is.null(weight)) NULL else hl_format_percent(row[[weight]] / total, 1))
  })
}

forest_spec <- function(data, study, estimate, low, high, weight = NULL, columns = character(), pooled = NULL,
                        ratio = TRUE, favours = NULL, colour, study_heading = "Study",
                        effect_heading = "Effect [95 % CI]", weight_heading = "Weight", digits = 2) {
  check_columns(data, c(study, estimate, low, high, weight, unname(columns)))
  forest_check_rows(data, study, low, high, ratio)
  rows <- forest_rows(data, study, estimate, low, high, weight, columns, digits)
  if (!is.null(pooled)) {
    pooled <- list(label = pooled$label %||% "Pooled", estimate = pooled$estimate, low = pooled$low,
                   high = pooled$high,
                   effect_text = hl_format_interval(pooled$estimate, pooled$low, pooled$high, digits))
  }
  intervals <- c(rows, if (is.null(pooled)) list() else list(pooled))
  axis <- forest_axis(vapply(intervals, `[[`, numeric(1), "low"), vapply(intervals, `[[`, numeric(1), "high"), ratio)
  list(rows = rows, columns = as.list(names(columns)), pooled = pooled, ratio = ratio, null = if (ratio) 1 else 0,
       favours = if (is.null(favours)) NULL else as.list(favours), axis = axis, color = colour,
       study_heading = study_heading, effect_heading = effect_heading,
       weight_heading = if (is.null(weight)) NULL else weight_heading)
}

forest_from_rma <- function(fit) {
  ratio <- fit$measure %in% c("OR", "RR", "HR", "IRR", "PETO", "ROM")
  back <- if (ratio) exp else identity
  spread <- stats::qnorm(0.975) * sqrt(fit$vi)
  table <- data.frame(study = as.character(fit$slab), estimate = back(fit$yi), low = back(fit$yi - spread),
                      high = back(fit$yi + spread), weight = stats::weights(fit))
  list(table = table, ratio = ratio,
       pooled = list(estimate = back(fit$b[1]), low = back(fit$ci.lb), high = back(fit$ci.ub), label = "Pooled"),
       heterogeneity = sprintf("I² = %s %%, tau² = %s", hl_format_number(fit$I2, 0),
                               hl_format_number(fit$tau2, 2)))
}

#' Forest plot
#'
#' A results table (study, extra columns, effect with 95 % interval, weight)
#' beside the intervals: squares sized by weight, a pooled diamond, a solid
#' null line, a dashed pooled line, a log axis for ratios and "favours"
#' labels under it. Heterogeneity goes into the caption.
#'
#' @param data A data frame of results, or a `metafor::rma` object.
#' @param study,estimate,low,high Columns: study label, effect and its interval limits.
#' @param weight Column of weights (any scale); squares get areas proportional to it.
#' @param columns Named character vector of extra text columns, `c("Events / n" = "events")`.
#' @param pooled `list(estimate = , low = , high = , label = )` for the pooled row.
#' @param ratio Effects are ratios (log axis, null line at 1); `FALSE` for differences.
#' @param favours Two labels for the left and right of the null line.
#' @param heterogeneity Text put at the start of the caption.
#' @param title,subtitle,caption Frame texts.
#' @param ... `study_heading`, `effect_heading`, `weight_heading`, `digits`.
#' @return A ggplot with the hairline frame.
#' @export
hl_forest <- function(data, study = "study", estimate = "estimate", low = "low", high = "high", weight = NULL,
                      columns = character(), pooled = NULL, ratio = TRUE, favours = NULL, heterogeneity = NULL,
                      title, subtitle = NULL, caption = NULL, ...) {
  if (inherits(data, "rma")) {
    converted <- forest_from_rma(data)
    data <- converted$table
    weight <- "weight"
    ratio <- converted$ratio
    pooled <- pooled %||% converted$pooled
    heterogeneity <- heterogeneity %||% converted$heterogeneity
  }
  spec <- forest_spec(data, study, estimate, low, high, weight, columns, pooled, ratio, favours,
                      colour = hl_settings()$palette[1], ...)
  parts <- c(heterogeneity, caption)
  note <- if (length(parts)) paste0(paste(sub("\\.$", "", parts), collapse = ". "), ".") else NULL
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title, subtitle = subtitle, caption = note, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) forest_drawing(spec, box, measure, style)
  plot
}
