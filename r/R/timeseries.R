# Small-multiple time series with two levels of detail; mirrors the Python timeseries().

rolling_mean <- function(values, window) {
  vapply(seq_along(values), function(index) mean(values[max(1, index - window + 1):index]), numeric(1))
}

check_columns <- function(data, columns) {
  for (column in columns) {
    if (!is.null(column) && !column %in% names(data)) {
      known <- paste(names(data), collapse = ", ")
      stop(sprintf("hairline: column '%s' is not in the data; columns: %s", column, known), call. = FALSE)
    }
  }
}

value_formatter <- function(percent) {
  if (percent) function(value, digits = 1) hl_format_percent(value, digits) else
    function(value, digits = 1) hl_format_number(value, digits)
}

panel_stats <- function(values, stats, percent, threshold, share_label) {
  show <- value_formatter(percent)
  result <- character()
  for (stat in stats) {
    if (stat == "share_above") {
      if (is.null(threshold)) stop("hairline: stats 'share_above' needs threshold =", call. = FALSE)
      result[[share_label]] <- hl_format_percent(mean(values >= threshold), 0)
    } else if (stat == "range") {
      result[["Range"]] <- paste0(show(min(values), 0), "–", show(max(values), 0))
    } else if (stat %in% c("mean", "median")) {
      value <- if (stat == "mean") mean(values) else stats::median(values)
      result[[if (stat == "mean") "Mean" else "Median"]] <- show(value)
    } else {
      stop(sprintf("hairline: unknown stat '%s'; use mean, median, range or share_above", stat), call. = FALSE)
    }
  }
  result
}

prepared_series <- function(data, x, y, by, order, window) {
  groups <- if (is.null(by)) "" else (order %||% unique(as.character(data[[by]])))
  data$.group <- factor(if (is.null(by)) "" else as.character(data[[by]]), levels = groups)
  data <- data[order(data$.group, data[[x]]), , drop = FALSE]
  data$.mean <- stats::ave(data[[y]], data$.group, FUN = function(values) rolling_mean(values, window))
  data
}

as_axis_value <- function(value, data_x) if (inherits(data_x, "Date")) as.Date(value) else value

panel_frame <- function(values, panels, groups) {
  targets <- panels %||% groups
  data.frame(values[rep(1, length(targets)), , drop = FALSE], .group = factor(targets, levels = groups),
             row.names = NULL)
}

mark_layers <- function(bands, events, data_x, groups) {
  settings <- hl_settings()
  layers <- list()
  for (band in bands) {
    frame <- panel_frame(data.frame(xmin = as_axis_value(band$start, data_x), xmax = as_axis_value(band$end, data_x)),
                         band$panels, groups)
    band_layer <- ggplot2::geom_rect(data = frame, ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax),
                                     ymin = -Inf, ymax = Inf, fill = settings$neutral$band, inherit.aes = FALSE)
    band_layer$hairline_decoration <- TRUE
    layers[[length(layers) + 1]] <- band_layer
  }
  width <- pt_to_mm(hl_tokens()$reference$width * settings$base_size)
  for (event in events) {
    frame <- panel_frame(data.frame(xintercept = as_axis_value(event$x, data_x)), event$panels, groups)
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
                                    linewidth = pt_to_mm(lines$secondary * base), alpha = lines$secondary_opacity)
    raw_layer$hairline_secondary <- TRUE
    layers[[1]] <- raw_layer
  }
  c(layers, list(ggplot2::geom_line(ggplot2::aes(.data[[x]], .data$.mean, colour = .data$.group),
                                    linewidth = pt_to_mm(lines$data * base)),
                 ggplot2::scale_colour_manual(values = colours, guide = "none")))
}

period_mean_layer <- function(data, y) {
  means <- stats::aggregate(data[[y]], list(.group = data$.group), mean)
  ggplot2::geom_hline(data = means, ggplot2::aes(yintercept = .data$x), colour = hl_settings()$neutral$muted,
                      linetype = "32", linewidth = pt_to_mm(hl_tokens()$reference$width * hl_settings()$base_size))
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
#' @return A ggplot with the hairline frame.
#' @export
hl_timeseries <- function(data, x, y, by = NULL, title, subtitle = NULL, caption = NULL, window = 7, raw = TRUE,
                          period_mean = FALSE, percent = FALSE, threshold = NULL, threshold_label = NULL,
                          threshold_legend = NULL, stats = c("mean", "median"), share_label = NULL, key = NULL,
                          key_panels = NULL, highlight = NULL, qualifiers = list(), bands = list(), events = list(),
                          order = NULL, raw_label = "Raw values", mean_label = NULL) {
  check_columns(data, c(x, y, by))
  data <- prepared_series(data, x, y, by, order, window)
  colours <- stats::setNames(vapply(levels(data$.group), function(name) {
    if (is.null(by)) hl_settings()$palette[1] else hl_color(name)
  }, character(1)), levels(data$.group))
  share_label <- share_label %||% paste("≥", if (is.null(threshold)) "" else value_formatter(percent)(threshold, 0))
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
    list(x = as_axis_value(event$x, data[[x]]), label = event$label, panels = event$panels)
  })
  plot@meta$hairline_notes <- Filter(function(note) !is.null(note$label), notes)
  headers_for(plot, data, y, stats, percent, threshold, share_label, key, key_panels, qualifiers)
}
