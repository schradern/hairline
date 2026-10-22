# Small-multiple time series with two levels of detail; mirrors the Python timeseries().

# Trailing mean of the values present in each window, as in the Python package; NA where a window has none.
rolling_mean <- function(values, window) {
  vapply(seq_along(values), function(index) {
    present <- values[max(1, index - window + 1):index]
    present <- present[!is.na(present)]
    if (length(present)) mean(present) else NA_real_
  }, numeric(1))
}

check_window <- function(window) {
  if (!is.numeric(window) || length(window) != 1 || is.na(window) || window < 1 || window != round(window)) {
    stop(sprintf("hairline: timeseries: window must be a whole number of 1 or more; got %s",
                 paste(format(window), collapse = ", ")), call. = FALSE)
  }
}

value_formatter <- function(percent) {
  if (percent) function(value, digits = 1) hl_format_percent(value, digits) else
    function(value, digits = 1) hl_format_number(value, digits)
}

panel_stats <- function(values, stats, percent, threshold, share_label) {
  show <- value_formatter(percent)
  values <- as.numeric(values[!is.na(values)])
  digits <- auto_digits(values * if (percent) 100 else 1)
  extra <- if (is_whole(values) && !percent) 1 else 0
  result <- character()
  for (stat in stats) {
    if (stat == "share_above") {
      if (is.null(threshold)) stop("hairline: stats 'share_above' needs threshold =", call. = FALSE)
      result[[share_label]] <- hl_format_percent(mean(values >= threshold), 0)
    } else if (stat == "range") {
      result[["Range"]] <- paste0(show(min(values), digits), "\u2013", show(max(values), digits))
    } else if (stat %in% c("mean", "median")) {
      value <- if (stat == "mean") mean(values) else stats::median(values)
      places <- if (stat == "mean") digits + extra else quantile_places(value, digits, extra > 0)
      result[[if (stat == "mean") "Mean" else "Median"]] <- show(value, places)
    } else {
      stop(sprintf("hairline: unknown stat '%s'; use mean, median, range or share_above", stat), call. = FALSE)
    }
  }
  result
}

# ISO date text on x (2025-01-31, 2025-01-31T10:00) becomes dates, so the axis is a time axis, as hl_over_time()
# reads it; other text stays as it is.
with_iso_dates <- function(values) {
  if (!is.character(values) && !is.factor(values)) return(values)
  tryCatch(study_iso_dates(values, "x"), error = function(error) values)
}

prepared_series <- function(data, x, y, by, order, window) {
  groups <- chart_groups(data, by, order, "timeseries")
  if (!is.null(by)) data <- data[as.character(data[[by]]) %in% groups, , drop = FALSE]
  # A frame of its own (.x, .y, .group, .mean), so a data column with one of those names is never overwritten.
  frame <- data.frame(.x = data[[x]], .y = data[[y]],
                      .group = factor(if (is.null(by)) rep("", nrow(data)) else as.character(data[[by]]),
                                      levels = groups))
  frame <- frame[order(frame$.group, frame$.x), , drop = FALSE]
  frame$.mean <- stats::ave(frame$.y, frame$.group, FUN = function(values) rolling_mean(values, window))
  frame
}

# A band's or event's position on the x axis: a date (or ISO text) on a date or time axis, a number otherwise.
as_axis_value <- function(value, data_x, key) {
  shown <- if (is.character(value)) sprintf("'%s'", value) else paste(format(value), collapse = ", ")
  if (inherits(data_x, c("Date", "POSIXct"))) {
    parsed <- if (length(value) != 1 || is.numeric(value)) NA else tryCatch({
      if (inherits(data_x, "Date")) as.Date(value) else as.POSIXct(value, tz = attr(data_x, "tzone") %||% "")
    }, error = function(error) NA)
    if (is.na(parsed)) {
      stop(sprintf("hairline: timeseries: %s %s is not a date; the x axis holds dates, such as '2024-03-10'", key,
                   shown), call. = FALSE)
    }
    return(parsed)
  }
  if (!is.numeric(value) || length(value) != 1 || !is.finite(value)) {
    stop(sprintf("hairline: timeseries: %s %s is not a number; the x axis holds numbers", key, shown), call. = FALSE)
  }
  value
}

panel_frame <- function(values, panels, groups) {
  targets <- panels %||% groups
  data.frame(values[rep(1, length(targets)), , drop = FALSE], .group = factor(targets, levels = groups),
             row.names = NULL)
}

mark_layers <- function(bands, events, data_x, groups) {
  settings <- hl_settings()
  layers <- list()
  for (band in bands) {
    frame <- panel_frame(data.frame(xmin = as_axis_value(band$start, data_x, "band start"),
                                    xmax = as_axis_value(band$end, data_x, "band end")), band$panels, groups)
    band_layer <- ggplot2::geom_rect(data = frame, ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax),
                                     ymin = -Inf, ymax = Inf, fill = settings$neutral$band, inherit.aes = FALSE)
    band_layer$hairline_decoration <- TRUE
    layers[[length(layers) + 1]] <- band_layer
  }
  width <- pt_to_linewidth(hl_tokens()$reference$width * settings$base_size)
  for (event in events) {
    frame <- panel_frame(data.frame(xintercept = as_axis_value(event$x, data_x, "event x")), event$panels, groups)
    layers[[length(layers) + 1]] <- ggplot2::geom_vline(data = frame, ggplot2::aes(xintercept = .data$xintercept),
                                                        colour = settings$neutral$muted, linetype = "13",
                                                        linewidth = width)
  }
  layers
}

series_layers <- function(data, x, y, raw, colours) {
  lines <- hl_tokens()$lines
  base <- hl_settings()$base_size
  layers <- list()
  if (raw) {
    raw_layer <- ggplot2::geom_line(ggplot2::aes(.data[[x]], .data[[y]], colour = .data$.group),
                                    linewidth = pt_to_linewidth(lines$secondary * base),
                                    alpha = lines$secondary_opacity)
    raw_layer$hairline_secondary <- TRUE
    layers[[1]] <- raw_layer
  }
  c(layers, list(ggplot2::geom_line(ggplot2::aes(.data[[x]], .data$.mean, colour = .data$.group),
                                    linewidth = pt_to_linewidth(lines$data * base)),
                 ggplot2::scale_colour_manual(values = colours, guide = "none")))
}

period_mean_layer <- function(data, y) {
  means <- stats::aggregate(data[[y]], list(.group = data$.group), mean, na.rm = TRUE)
  ggplot2::geom_hline(data = means, ggplot2::aes(yintercept = .data$x), colour = hl_settings()$neutral$muted,
                      linetype = "32",
                      linewidth = pt_to_linewidth(hl_tokens()$reference$width * hl_settings()$base_size))
}

timeseries_legend <- function(raw, period_mean, bands, raw_label, mean_label, threshold_legend) {
  neutral <- hl_settings()$neutral
  items <- if (raw) list(list(kind = "thin", colour = neutral$ink, label = raw_label)) else list()
  items[[length(items) + 1]] <- list(kind = "line", colour = neutral$ink, label = mean_label)
  if (period_mean) items[[length(items) + 1]] <- list(kind = "dash", colour = neutral$muted, label = "Period mean")
  if (!is.null(threshold_legend)) {
    items[[length(items) + 1]] <- list(kind = "dash", colour = hl_tokens()$reference$color, label = threshold_legend)
  }
  if (length(bands) && !is.null(bands[[1]]$label)) {
    items[[length(items) + 1]] <- list(kind = "band", colour = neutral$band, label = bands[[1]]$label)
  }
  hl_legend(items)
}

headers_for <- function(plot, data, y, stats, percent, threshold, share_label, key, key_panels, qualifiers) {
  labels <- c(share_above = share_label, mean = "Mean", median = "Median", range = "Range")
  for (name in levels(data$.group)) {
    emphasise <- !is.null(key) && (is.null(key_panels) || name %in% key_panels)
    values <- data[[y]][data$.group == name]
    plot <- plot + hl_panel_header(panel = if (nzchar(name)) name else NULL, name = name,
                                   qualifier = qualifiers[[name]],
                                   stats = panel_stats(values, stats, percent, threshold, share_label),
                                   key = if (emphasise) unname(labels[key] %||% key) else NULL)
  }
  plot
}

#' Small-multiple time series with two levels of detail
#'
#' One panel per group: raw values as a thin line under a trailing rolling
#' mean in the group's entity colour, with key numbers in the panel headers,
#' and optional period mean, threshold, highlighted periods and events.
#'
#' @param data A data frame.
#' @param x,y,by Column names: time, value and the grouping (one panel per group).
#' @param title,subtitle,caption Frame texts.
#' @param window Rolling-mean window in rows (trailing, partial windows at the start).
#' @param raw Draw the raw values.
#' @param period_mean Draw each panel's mean as a dashed line.
#' @param percent Values are shares; label axis and key numbers as percentages.
#' @param threshold,threshold_label,threshold_legend Reference line, its label and legend entry.
#' @param stats Key numbers: any of `"mean"`, `"median"`, `"range"`, `"share_above"`.
#' @param share_label Label of the `"share_above"` key number.
#' @param key,key_panels The key number to emphasise and the panels to emphasise it in.
#' @param highlight Panels to keep in colour; the others become context grey.
#' @param qualifiers Named list of qualifier texts per group, e.g. bed counts.
#' @param bands List of `list(start, end, label)` highlighted periods.
#' @param events List of `list(x, label)` event markers.
#' @param order Group order; defaults to the order of appearance.
#' @param raw_label,mean_label Legend labels of the two lines.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame; [hl_save()] writes it at the `"double"` size (174 mm) unless told
#'   otherwise, as the Python package does.
#' @examples
#' set.seed(1)
#' occupancy <- data.frame(date = rep(as.Date("2025-01-01") + 0:89, 2),
#'                         unit = rep(c("Unit A", "Unit B"), each = 90),
#'                         share = pmin(1, c(0.8 + stats::rnorm(90, 0, 0.05),
#'                                           0.7 + stats::rnorm(90, 0, 0.05))))
#' hl_timeseries(occupancy, "date", "share", by = "unit", percent = TRUE, threshold = 0.9,
#'               threshold_label = "90 %")
#' @export
hl_timeseries <- function(data, x, y, by = NULL, title = NULL, subtitle = NULL, caption = NULL, window = 7, raw = TRUE,
                          period_mean = FALSE, percent = FALSE, threshold = NULL, threshold_label = NULL,
                          threshold_legend = NULL, stats = c("mean", "median"), share_label = NULL, key = NULL,
                          key_panels = NULL, highlight = NULL, qualifiers = list(), bands = list(), events = list(),
                          order = NULL, raw_label = "Raw values", mean_label = NULL, colors = NULL) {
  check_columns(data, c(x, y, by))
  title <- title %||% if (is.null(by)) paste(humanise(y), "over time") else paste(humanise(y), "by", gsub("_", " ", by))
  check_window(window)
  check_present(data, y, "timeseries")
  check_numeric(data, y, "timeseries")
  data[[x]] <- with_iso_dates(data[[x]])
  data <- prepared_series(data, x, y, by, order, window)
  x <- ".x"
  y <- ".y"
  colours <- if (is.null(by)) stats::setNames(lone_colour(), levels(data$.group)) else
    colours_for(levels(data$.group), colors)
  threshold_text <- if (is.null(threshold)) "" else value_formatter(percent)(threshold, 0)
  share_label <- share_label %||% paste("\u2265", threshold_text)
  plot <- ggplot2::ggplot(data) + mark_layers(bands, events, data[[x]], levels(data$.group))
  if (period_mean) plot <- plot + period_mean_layer(data, y)
  plot <- plot + series_layers(data, x, y, raw, colours) + ggplot2::facet_wrap(~.group, ncol = 1) +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = NULL, y = NULL) + theme_hairline() +
    timeseries_legend(raw, period_mean, bands, raw_label, mean_label %||% sprintf("Rolling mean (%d)", window),
                      threshold_legend)
  if (percent) plot <- plot + scale_y_hairline(percent = TRUE)
  if (!is.null(threshold)) plot <- plot + hl_reference(y = threshold, label = threshold_label)
  if (!is.null(highlight)) plot <- plot + hl_highlight(panels = highlight)
  notes <- lapply(events, function(event) {
    list(x = as_axis_value(event$x, data[[x]], "event x"), label = event$label, panels = event$panels)
  })
  plot@meta$hairline_notes <- Filter(function(note) !is.null(note$label), notes)
  plot <- headers_for(plot, data, y, stats, percent, threshold, share_label, key, key_panels, qualifiers)
  # Panels in rows across the page, as the Python package's default size.
  plot@meta$hairline_size <- "double"
  plot
}
