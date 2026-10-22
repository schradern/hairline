# Forest plot: a results table with intervals, weighted squares and a pooled diamond;
# mirrors the Python forest().

exact_tolerance <- 1e-12

# The fewest decimals that show every value exactly (axis breaks: 0.2, 0.0005), up to study.max_digits, or two
# significant digits of the smallest value too small to show within it (1e-9).
forest_decimals <- function(values) {
  shown <- abs(values[values != 0])
  most <- capped_places(hl_tokens()$study$max_digits, if (length(shown)) min(shown) else 0)
  for (digits in 0:most) {
    if (all(abs(round(values, digits) - values) <= exact_tolerance * pmin(1, abs(values)))) return(digits)
  }
  most
}

# Two decimals, or more where the estimates and limits are small or close together (0.0004 [0.0003; 0.0005]).
forest_default_digits <- function(data, columns) max(2, auto_digits(unlist(data[columns], use.names = FALSE)))

forest_axis <- function(lows, highs, ratio, null) {
  low <- min(c(lows, null))
  high <- max(c(highs, null))
  if (low == high) {
    # every value alike: an axis around it, a factor of two for ratios
    pad <- if (low == 0) 1 else abs(low)
    limits <- if (ratio) c(low / 2, high * 2) else c(low - pad, high + pad)
    low <- limits[1]
    high <- limits[2]
  }
  breaks <- if (ratio) log_breaks(low, high, hl_tokens()$forest$max_ticks) else nice_breaks(low, high)
  limits <- if (ratio) range(breaks) else axis_limits(low, high, breaks)
  shared <- forest_decimals(breaks)
  labels <- vapply(breaks, function(value) hl_format_number(value, if (ratio) forest_decimals(value) else shared),
                   character(1))
  list(breaks = breaks, labels = labels, low = limits[1], high = limits[2])
}

# Present, ordered limits around their estimate, above zero on a ratio scale.
forest_check_interval <- function(name, estimate, low, high, ratio) {
  values <- c(estimate, low, high)
  if (!is.numeric(values) || length(values) != 3 || !all(is.finite(values))) {
    stop(sprintf("hairline: forest: '%s' has estimate %s, low %s and high %s; all three must be numbers", name,
                 format(estimate), format(low), format(high)), call. = FALSE)
  }
  if (low > high) stop(sprintf("hairline: forest: '%s' has a lower limit above its upper limit", name), call. = FALSE)
  if (estimate < low || estimate > high) {
    stop(sprintf("hairline: forest: '%s' has its estimate %s outside its interval [%s; %s]", name,
                 format(estimate), format(low), format(high)), call. = FALSE)
  }
  if (ratio && low <= 0) {
    stop(sprintf("hairline: forest: '%s' has a limit of 0 or below on a ratio scale; pass ratio = FALSE for %s",
                 name, "differences"), call. = FALSE)
  }
}

forest_check_rows <- function(data, study, estimate, low, high, weight, ratio) {
  if (!nrow(data)) stop("hairline: forest: no rows to draw", call. = FALSE)
  for (index in seq_len(nrow(data))) {
    forest_check_interval(as.character(data[[study]][index]), data[[estimate]][index], data[[low]][index],
                          data[[high]][index], ratio)
  }
  if (!is.null(weight)) {
    weights <- data[[weight]]
    if (!is.numeric(weights) || !all(is.finite(weights) & weights >= 0) || !(sum(weights) > 0)) {
      stop(sprintf("hairline: forest: '%s' must hold weights of 0 or more that add up to more than 0; got %s",
                   weight, paste(format(weights), collapse = ", ")), call. = FALSE)
    }
  }
}

forest_checked_pooled <- function(pooled, ratio) {
  missing <- setdiff(c("estimate", "low", "high"), names(pooled))
  if (length(missing)) {
    stop(sprintf("hairline: forest: pooled needs estimate, low and high; missing %s",
                 paste(missing, collapse = ", ")), call. = FALSE)
  }
  forest_check_interval(pooled$label %||% "Pooled", pooled$estimate, pooled$low, pooled$high, ratio)
  pooled
}

forest_rows <- function(data, study, estimate, low, high, weight, columns, digits, interval = TRUE) {
  total <- if (is.null(weight)) NULL else sum(data[[weight]])
  lapply(seq_len(nrow(data)), function(index) {
    row <- data[index, , drop = FALSE]
    list(study = as.character(row[[study]]), estimate = row[[estimate]], low = row[[low]], high = row[[high]],
         weight = if (is.null(weight)) NULL else row[[weight]],
         cells = lapply(unname(columns), function(column) as.character(row[[column]])),
         effect_text = if (interval) hl_format_interval(row[[estimate]], row[[low]], row[[high]], digits) else
           hl_format_number(row[[estimate]], digits),
         weight_text = if (is.null(weight)) NULL else hl_format_percent(row[[weight]] / total, 1))
  })
}

forest_spec <- function(data, study, estimate, low, high, weight = NULL, columns = character(), pooled = NULL,
                        ratio = TRUE, favours = NULL, colour, study_heading = "Study",
                        effect_heading = "Effect [95 % CI]", weight_heading = "Weight", digits = NULL,
                        marker = "square", interval = TRUE, null = "auto") {
  check_columns(data, c(study, estimate, low, high, weight, unname(columns)))
  forest_check_rows(data, study, estimate, low, high, weight, ratio)
  if (!is.null(favours) && length(favours) != 2) {
    stop(sprintf("hairline: forest: favours takes two labels (left, right); got %d", length(favours)), call. = FALSE)
  }
  if (!is.null(pooled)) pooled <- forest_checked_pooled(as.list(pooled), ratio)
  digits <- digits %||% forest_default_digits(data, c(estimate, low, high))
  rows <- forest_rows(data, study, estimate, low, high, weight, columns, digits, interval)
  if (identical(null, "auto")) null <- if (ratio) 1 else 0
  if (!is.null(pooled)) {
    pooled <- list(label = pooled$label %||% "Pooled", estimate = pooled$estimate, low = pooled$low,
                   high = pooled$high,
                   effect_text = hl_format_interval(pooled$estimate, pooled$low, pooled$high, digits))
  }
  intervals <- c(rows, if (is.null(pooled)) list() else list(pooled))
  axis <- forest_axis(vapply(intervals, `[[`, numeric(1), "low"), vapply(intervals, `[[`, numeric(1), "high"), ratio,
                      null)
  list(rows = rows, columns = as.list(names(columns)), pooled = pooled, ratio = ratio, null = null, marker = marker,
       favours = if (is.null(favours)) NULL else as.list(favours), axis = axis, color = colour,
       study_heading = study_heading, effect_heading = effect_heading,
       weight_heading = if (is.null(weight)) NULL else weight_heading)
}

forest_from_model <- function(model, exponentiate) {
  link <- if (inherits(model, "glm")) model$family$link else ""
  exponentiate <- exponentiate %||% (inherits(model, "coxph") || link %in% c("logit", "log"))
  estimates <- stats::coef(model)
  # The model's own 95 % intervals: Student t for lm (as confint() and Python's statsmodels give them), Wald for glm
  # and coxph (as summary() and statsmodels report them; confint() would profile a glm instead).
  limits <- if (inherits(model, "lm") && !inherits(model, "glm")) stats::confint(model) else
    stats::confint.default(model)
  keep <- names(estimates) != "(Intercept)"
  aliased <- keep & is.na(estimates)
  if (any(aliased)) {
    warning(sprintf("hairline: terms without an estimate (aliased with others) are left out: %s",
                    paste(names(estimates)[aliased], collapse = ", ")), call. = FALSE)
  }
  keep <- keep & !aliased
  if (!any(keep)) stop("hairline: the model has no terms with an estimate besides the intercept", call. = FALSE)
  limits <- limits[names(estimates), , drop = FALSE]
  back <- if (exponentiate) exp else identity
  list(ratio = exponentiate,
       table = data.frame(term = names(estimates)[keep], estimate = back(unname(estimates[keep])),
                          low = back(unname(limits[keep, 1])), high = back(unname(limits[keep, 2]))))
}

forest_from_rma <- function(fit) {
  ratio <- fit$measure %in% c("OR", "RR", "HR", "IRR", "PETO", "ROM")
  back <- if (ratio) exp else identity
  spread <- stats::qnorm(0.975) * sqrt(fit$vi)
  table <- data.frame(study = as.character(fit$slab), estimate = back(fit$yi), low = back(fit$yi - spread),
                      high = back(fit$yi + spread), weight = stats::weights(fit))
  list(table = table, ratio = ratio,
       pooled = list(estimate = back(fit$b[1]), low = back(fit$ci.lb), high = back(fit$ci.ub), label = "Pooled"),
       heterogeneity = sprintf("I\u00b2 = %s %%, tau\u00b2 = %s", hl_format_number(fit$I2, 0),
                               hl_format_number(fit$tau2, 2)))
}

#' Forest plot
#'
#' A results table (study, extra columns, effect with 95 % interval, weight)
#' beside the intervals: squares sized by weight, a pooled diamond, a solid
#' null line, a dashed pooled line, a log axis for ratios and "favours"
#' labels under it. Heterogeneity goes into the caption. On a figure too narrow
#' for the columns beside the intervals, they sit on a line under each study.
#'
#' @param data A data frame of results, a fitted `lm`, `glm` or `survival::coxph` model, or a `metafor::rma`
#'   object.
#' @param study,estimate,low,high Columns: study label, effect and its interval limits.
#' @param weight Column of weights (any scale); squares get areas proportional to it.
#' @param columns Named character vector of extra text columns, `c("Events / n" = "events")`.
#' @param pooled `list(estimate = , low = , high = , label = )` for the pooled row.
#' @param ratio Effects are ratios (log axis, null line at 1); `FALSE` for differences.
#' @param favours Two labels for the left and right of the null line.
#' @param heterogeneity Text put at the start of the caption.
#' @param title,subtitle,caption Frame texts.
#' @param exponentiate For fitted models: report exp(coefficient) (odds, rate or hazard ratios); `NULL` decides
#'   from the model (logit and log links, Cox models).
#' @param ... `study_heading`, `effect_heading`, `weight_heading`, `digits`.
#' @return A ggplot with the hairline frame.
#' @examples
#' trials <- data.frame(study = c("Trial A", "Trial B", "Trial C"), or = c(0.62, 0.81, 0.47),
#'                      low = c(0.41, 0.55, 0.25), high = c(0.94, 1.19, 0.88), weight = c(40, 35, 25))
#' hl_forest(trials, "study", "or", "low", "high", weight = "weight",
#'           pooled = list(estimate = 0.66, low = 0.52, high = 0.84, label = "Pooled"))
#' @export
hl_forest <- function(data, study = "study", estimate = "estimate", low = "low", high = "high", weight = NULL,
                      columns = character(), pooled = NULL, ratio = TRUE, favours = NULL, heterogeneity = NULL,
                      title = NULL, subtitle = NULL, caption = NULL, exponentiate = NULL, ...) {
  if (inherits(data, c("lm", "coxph"))) {
    converted <- forest_from_model(data, exponentiate)
    data <- converted$table
    study <- "term"
    estimate <- "estimate"
    low <- "low"
    high <- "high"
    ratio <- converted$ratio
  }
  title <- title %||% paste("Effects by", tolower(humanise(study)))
  if (inherits(data, "rma")) {
    converted <- forest_from_rma(data)
    data <- converted$table
    weight <- "weight"
    ratio <- converted$ratio
    pooled <- pooled %||% converted$pooled
    heterogeneity <- heterogeneity %||% converted$heterogeneity
  }
  spec <- forest_spec(data, study, estimate, low, high, weight, columns, pooled, ratio, favours,
                      colour = lone_colour(), ...)
  parts <- c(heterogeneity, caption)
  note <- if (length(parts)) paste0(paste(sub("\\.$", "", parts), collapse = ". "), ".") else NULL
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title, subtitle = subtitle, caption = note, x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) forest_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
