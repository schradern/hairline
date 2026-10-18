# Kaplan–Meier curves, mirroring the Python kaplan_meier(): step curves with bands and censor
# ticks, medians and user statistics in the panel header, the number at risk under the x-axis.

km_from_fit <- function(fit) {
  strata <- if (is.null(fit$strata)) stats::setNames(length(fit$time), "") else fit$strata
  ends <- cumsum(strata)
  lapply(seq_along(strata), function(index) {
    rows <- (ends[index] - strata[index] + 1):ends[index]
    list(name = sub("^[^=]*=", "", names(strata)[index]), total = fit$n[index],
         table = data.frame(time = fit$time[rows], at_risk = fit$n.risk[rows], events = fit$n.event[rows],
                            censored = fit$n.censor[rows], survival = fit$surv[rows], low = fit$lower[rows],
                            high = fit$upper[rows]))
  })
}

km_from_data <- function(data, time, event, by, order) {
  check_columns(data, c(time, event, by))
  groups <- if (is.null(by)) "" else (order %||% unique(as.character(data[[by]])))
  lapply(groups, function(name) {
    rows <- if (is.null(by)) data else data[as.character(data[[by]]) == name, , drop = FALSE]
    list(name = name, total = nrow(rows), table = km_estimate(rows[[time]], rows[[event]]))
  })
}

km_at_risk <- function(table, total, moments) {
  vapply(moments, function(moment) {
    later <- table$at_risk[table$time >= moment]
    if (length(later)) later[1] else 0
  }, numeric(1))
}

stepped <- function(x, y) {
  count <- length(x)
  if (count < 2) return(list(x = x, y = y))
  list(x = c(x[1], rep(x[-1], each = 2)), y = c(rep(y[-count], each = 2), y[count]))
}

km_layer_data <- function(estimates) {
  curves <- bands <- censored <- list()
  for (estimate in estimates) {
    table <- estimate$table
    curves[[length(curves) + 1]] <- data.frame(time = c(0, table$time), survival = c(1, table$survival),
                                               group = estimate$name)
    banded <- table[!is.na(table$low) & !is.na(table$high), , drop = FALSE]
    low <- stepped(c(0, banded$time), c(1, banded$low))
    high <- stepped(c(0, banded$time), c(1, banded$high))
    bands[[length(bands) + 1]] <- data.frame(time = low$x, low = low$y, high = high$y, group = estimate$name)
    marks <- table[table$censored > 0, , drop = FALSE]
    censored[[length(censored) + 1]] <- data.frame(time = marks$time, survival = marks$survival,
                                                   group = rep(estimate$name, nrow(marks)))
  }
  levels <- vapply(estimates, `[[`, character(1), "name")
  lapply(list(curves = do.call(rbind, curves), bands = do.call(rbind, bands), censored = do.call(rbind, censored)),
         function(frame) transform(frame, group = factor(frame$group, levels = levels)))
}

km_layers <- function(layers, colours, median_line) {
  rules <- hl_tokens()$survival
  base <- hl_settings()$base_size
  width <- pt_to_mm(hl_tokens()$lines$data * base)
  band <- ggplot2::geom_ribbon(data = layers$bands, ggplot2::aes(.data$time, ymin = .data$low, ymax = .data$high,
                                                                 fill = .data$group, group = .data$group),
                               alpha = rules$band_opacity, inherit.aes = FALSE)
  curve <- ggplot2::geom_step(data = layers$curves, ggplot2::aes(.data$time, .data$survival, colour = .data$group),
                              linewidth = width, direction = "hv", inherit.aes = FALSE)
  ticks <- ggplot2::geom_point(data = layers$censored, ggplot2::aes(.data$time, .data$survival, colour = .data$group),
                               shape = 124, size = pt_to_mm(rules$censor_tick * base / 0.75), alpha = 1,
                               inherit.aes = FALSE)
  range <- ggplot2::geom_blank(data = data.frame(time = 0, survival = c(0, 1)),
                               ggplot2::aes(.data$time, .data$survival), inherit.aes = FALSE)
  result <- list(band, curve, ticks, range, ggplot2::scale_colour_manual(values = colours),
                 ggplot2::scale_fill_manual(values = colours, guide = "none"))
  if (!median_line) return(result)
  c(result, list(ggplot2::geom_hline(yintercept = 0.5, colour = hl_tokens()$reference$color, linetype = "13",
                                     linewidth = pt_to_mm(hl_tokens()$reference$width * base))))
}

#' Kaplan–Meier curves
#'
#' Step curves per group with 95 % bands (Greenwood, log scale) and censor
#' ticks, a dotted 50 % line, medians and your statistics in the panel
#' header, and the number at risk under the x-axis aligned to its ticks.
#'
#' @param data A data frame, or a `survival::survfit` object.
#' @param time,event Columns with follow-up time and event (1 = event, 0 = censored); unused for `survfit`.
#'   `time` may also be a formula `Surv(time, event) ~ group`.
#' @param by Grouping column; one curve per group.
#' @param title,subtitle,caption Frame texts.
#' @param x_title Axis title under the x-axis.
#' @param endpoint Panel header name, e.g. `"Overall survival"`.
#' @param median_line Draw the dotted 50 % line.
#' @param stats Named character vector of key numbers, e.g. `c(HR = "0.64 [0.45, 0.91]")`.
#' @param at_risk Show the number at risk.
#' @param times Times for the number at risk; default the x-axis breaks.
#' @param order Group order.
#' @param test Add the log-rank p to the key numbers when there are groups.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#2474cf")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame.
#' @export
hl_kaplan_meier <- function(data, time = NULL, event = NULL, by = NULL, title = NULL, subtitle = NULL, caption = NULL,
                            x_title = "Time", endpoint = "Survival", median_line = TRUE, stats = character(),
                            at_risk = TRUE, times = NULL, order = NULL, test = TRUE, colors = NULL) {
  if (inherits(time, "formula")) {
    sides <- formula_sides(time)
    time <- as.character(sides$left[[2]])
    event <- as.character(sides$left[[3]])
    by <- if (length(sides$right)) sides$right[1] else NULL
  }
  title <- title %||% if (is.null(by)) endpoint else paste(endpoint, "by", gsub("_", " ", by))
  if (!inherits(data, "survfit") && !is.null(by) && test && !any(startsWith(tolower(names(stats)), "log-rank"))) {
    stats <- c(stats, `Log-rank` = format_p(logrank_test(data[[time]], data[[event]], data[[by]])$p))
  }
  estimates <- if (inherits(data, "survfit")) km_from_fit(data) else km_from_data(data, time, event, by, order)
  grouped <- !is.null(by) || length(estimates) > 1
  names <- vapply(estimates, function(estimate) if (nzchar(estimate$name)) estimate$name else endpoint, character(1))
  for (index in seq_along(estimates)) estimates[[index]]$name <- names[index]
  colours <- if (grouped) colours_for(names, colors) else stats::setNames(hl_settings()$palette[1], names)
  max_time <- max(vapply(estimates, function(estimate) max(estimate$table$time), numeric(1)))
  moments <- times %||% nice_breaks(0, max_time)
  medians <- paste(vapply(estimates, function(estimate) {
    median <- km_median(estimate$table)
    if (is.null(median)) "not reached" else hl_format_number(median, 1)
  }, character(1)), collapse = " vs ")
  plot <- ggplot2::ggplot() + km_layers(km_layer_data(estimates), colours, median_line) +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = x_title, y = NULL) + theme_hairline() +
    scale_y_hairline(percent = TRUE) + hl_panel_header(name = endpoint, stats = c(Median = medians, stats))
  if (!grouped) plot <- plot + hl_legend(list())
  if (at_risk) {
    rows <- lapply(seq_along(estimates), function(index) {
      counts <- km_at_risk(estimates[[index]]$table, estimates[[index]]$total, moments)
      list(label = names[index], colour = unname(colours[index]), x = moments,
           text = vapply(counts, hl_format_number, character(1), digits = 0))
    })
    plot@meta$hairline_table <- list(heading = "Number at risk", rows = rows)
  }
  plot
}
