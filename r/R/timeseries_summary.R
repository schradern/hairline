# hl_timeseries(summary = ...), mirroring the Python timeseries_summary.py: the values at each x summarised, a centre
# line over its interval band, and the key numbers of the panel headers, named as on every distribution chart
# (summaries.R).

timeseries_stats <- c(stat_names, "share_above")

# The centre and interval drawn over time, or NULL for the raw values under a rolling mean.
timeseries_summary <- function(summary) {
  if (is.null(summary)) NULL else check_paired(check_summary(summary, "timeseries"), "timeseries")
}

# Per panel and x, in order: the centre and the interval's ends (NaN where an SD or CI has one value only).
summary_series <- function(data, marks) {
  present <- data[!is.na(data$.y), , drop = FALSE]
  keys <- unique(present[order(present$.group, present$.x), c(".group", ".x")])
  rows <- lapply(seq_len(nrow(keys)), function(index) {
    values <- present$.y[present$.group == keys$.group[index] & present$.x == keys$.x[index]]
    found <- summary_values(values)
    ends <- if (is.null(marks$interval)) c(NaN, NaN) else interval_of(found, marks$interval)
    data.frame(.group = keys$.group[index], .x = keys$.x[index], .centre = found[[marks$centre]], .low = ends[1],
               .high = ends[2])
  })
  do.call(rbind, rows)
}

# The interval as a band in the series' colour, the centre as its line over it.
summary_series_layers <- function(data, marks, colours) {
  lines <- hl_tokens()$lines
  base <- hl_settings()$base_size
  series <- summary_series(data, marks)
  band <- if (!is.null(marks$interval)) {
    layer <- ggplot2::geom_ribbon(data = series, ggplot2::aes(.data$.x, ymin = .data$.low, ymax = .data$.high,
                                                              fill = .data$.group),
                                  alpha = lines$band_opacity, colour = NA, inherit.aes = FALSE)
    layer$hairline_secondary <- TRUE
    list(layer)
  }
  c(band, list(ggplot2::geom_line(data = series, ggplot2::aes(.data$.x, .data$.centre, colour = .data$.group),
                                  linewidth = pt_to_linewidth(lines$data * base), inherit.aes = FALSE),
               ggplot2::scale_colour_manual(values = colours, guide = "none"),
               ggplot2::scale_fill_manual(values = colours, guide = "none")))
}

# The centre's line and the interval's band, in ink and in ink over the surface at the band's opacity.
summary_series_legend <- function(marks) {
  neutral <- hl_settings()$neutral
  items <- list(list(kind = "line", colour = neutral$ink, label = word(marks$centre)))
  if (!is.null(marks$interval)) {
    ink <- grDevices::col2rgb(neutral$ink)[, 1] / 255
    surface <- grDevices::col2rgb(neutral$surface)[, 1] / 255
    mixed <- surface + (ink - surface) * hl_tokens()$lines$band_opacity
    items[[2]] <- list(kind = "band", colour = tolower(grDevices::rgb(mixed[1], mixed[2], mixed[3])),
                       label = word(summary_legend_words[[marks$interval]]))
  }
  items
}

# A panel's key numbers: any shared measure (stats =) and the share at or above `threshold`.
panel_stats <- function(values, stats, percent, threshold, share_label) {
  names <- as_names(stats, "timeseries", "stats", timeseries_stats)
  values <- as.numeric(values[!is.na(values)])
  measures <- setdiff(names, "share_above")
  found <- if (length(values)) {
    stats::setNames(stat_pairs(values, measures, measure_numbers(values, percent, NULL)), measures)
  } else {
    stats::setNames(lapply(measures, function(name) c(stat_label(name), "\u2013")), measures)
  }
  result <- character()
  for (name in names) {
    if (name == "share_above") {
      if (is.null(threshold)) stop("hairline: stats 'share_above' needs threshold =", call. = FALSE)
      result[[share_label]] <- if (length(values)) hl_format_percent(mean(values >= threshold), 0) else "\u2013"
    } else {
      result[[found[[name]][1]]] <- found[[name]][2]
    }
  }
  result
}
