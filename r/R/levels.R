# Counts of people (or places) over the time of day as steps on whole-number levels, mirroring the Python levels():
# how often exactly 1, 2, 3 ... were needed (one shaded row per count, as lanes shade their cells), the typical day
# (median, dashed) and the count that is enough on most days (the decision line, bold). Quantiles stay on the data's
# levels: people only come whole.

# Counts sampled at times: each (day, bin)'s peak; a bin without a sample counts as 0, nobody needed.
sample_peaks <- function(rows, time, count, origin, total, bin) {
  times <- as_times(rows[[time]], time, "levels")
  minutes <- floor(as.numeric(times - origin, units = "mins") + 1e-9)
  values <- numeric(total * day_minutes)
  slots <- pmin(pmax(minutes, 0), total * day_minutes - 1) + 1
  for (index in seq_along(slots)) values[slots[index]] <- max(values[slots[index]], rows[[count]][index])
  binned(values, bin, "peak")
}

check_quantile <- function(quantile) {
  if (!(is.numeric(quantile) && length(quantile) == 1 && quantile > 0 && quantile < 1)) {
    stop(sprintf("hairline: levels: quantile must lie between 0 and 1 (0.9: enough on 9 of 10 days); got %s",
                 paste(format(quantile), collapse = ", ")), call. = FALSE)
  }
  as.numeric(quantile)
}

# Per group the peak per kept day and bin: from intervals (people or patients present at once) or from counts sampled
# at times.
peaks_per_group <- function(data, time, count, end, by, bin, days, order) {
  if (!is.null(end)) {
    times <- interval_rows(data, time, end, "levels")
    origin <- day_start(times$starts)
    total <- day_count(times$starts, times$ends)
  } else {
    check_numeric(data, count, "levels")
    times <- as_times(data[[time]], time, "levels")
    origin <- day_start(times)
    total <- day_count(times, times)
  }
  kept <- calendar(origin, total, days, "levels")
  names <- if (is.null(by)) "" else chart_groups(data, by, order, "levels")
  peaks <- lapply(names, function(name) {
    rows <- if (is.null(by)) data else data[as.character(data[[by]]) == name, , drop = FALSE]
    found <- if (!is.null(end)) {
      spans <- interval_rows(rows, time, end, "levels")
      binned(minute_counts(spans$starts, spans$ends, origin, total), bin, "peak")
    } else {
      sample_peaks(rows, time, count, origin, total, bin)
    }
    found[kept$rows + 1, , drop = FALSE]
  })
  list(groups = stats::setNames(peaks, names), label = kept$label)
}

# A steps-post line over the bins shown, ending at the last bin's end.
step_frame <- function(values, bins, bin) {
  data.frame(x = c((bins - 1) * bin / 60, bins[length(bins)] * bin / 60),
             y = c(values[bins], values[bins[length(bins)]]))
}

# One shaded row per count from 1 up: each bin's share of days that needed exactly that many, binned as the key shows.
level_cells <- function(name, peaks, bins, colour, steps, bin) {
  ramp <- step_colours(colour, length(steps))
  half <- hl_tokens()$lanes$cell / 2
  cells <- list()
  for (level in seq_len(max(peaks))) {
    shares <- colMeans(peaks[, bins, drop = FALSE] == level)
    shown <- bins[shares > 0]
    shares <- shares[shares > 0]
    if (!length(shown)) next
    low <- (shown - 1) * bin / 60
    high <- low + bin / 60
    prefix <- if (nzchar(name)) paste0(name, ": ") else ""
    cells[[level]] <- data.frame(name = paste(if (nzchar(name)) name else "Count", level), colour = colour, x0 = low,
                                 x1 = high, y0 = level - half, y1 = level + half,
                                 fill = ramp[vapply(shares, step_index, 1, steps = steps)],
                                 text = paste0(prefix, hl_format_number(level, 0), ", ", clock(low), "\u2013",
                                               clock(high), ": ", vapply(shares, hl_format_percent, "", digits = 0)))
  }
  do.call(rbind, cells)
}

level_line_layers <- function(name, peaks, bins, quantile, typical, bin) {
  settings <- hl_settings()
  rules <- hl_tokens()$levels
  base <- settings$base_size
  decision <- apply(peaks, 2, function(values) level_quantiles(values, quantile))
  layers <- list()
  middle <- NULL
  if (!is.null(typical)) {
    middle <- apply(peaks, 2, function(values) level_quantiles(values, 0.5))
    dash <- paste(sprintf("%X", as.integer(round(unlist(rules$typical_dash)))), collapse = "")
    width <- pt_to_linewidth(hl_tokens()$reference$width * base * 1.5)
    layers[[1]] <- static_layer(ggplot2::geom_step(data = step_frame(middle, bins, bin), ggplot2::aes(.data$x, .data$y),
                                                   colour = settings$neutral$muted, linetype = dash, linewidth = width))
  }
  share <- hl_format_percent(quantile, 0)
  line <- ggplot2::geom_step(data = step_frame(decision, bins, bin), ggplot2::aes(.data$x, .data$y),
                             colour = settings$neutral$ink, linejoin = "mitre",
                             linewidth = pt_to_linewidth(rules$decision_width * base))
  line$hairline_series <- if (nzchar(name)) paste0(name, ": ", word("decision", share = share)) else
    word("decision", share = share)
  list(layers = c(layers, list(line)), decision = decision, middle = middle)
}

#' Whole counts over the time of day
#'
#' One panel per group of `by` (doctors, nurses): from intervals (`time` the
#' start, `end` the end: the people present at once) or from counts sampled at
#' times (`count`). Per `bin`, each day's peak; then the share of days that
#' needed exactly 1, 2, 3 ... (`shade`, binned at `steps`), the typical day (the
#' median, dashed; `typical = NULL` leaves it out) and the count that is enough
#' on `quantile` of the days (0.9 by default; bold). Both lines are steps on the
#' data's levels (quantile type 1), and the panel header gives their highest
#' values ("Up to 3 · Typical 2").
#'
#' @param data A data frame.
#' @param time Column with the start of each interval, or the time of each count.
#' @param count Column with counts sampled at times.
#' @param end Column with the end of each interval.
#' @param by Grouping column: one panel per group.
#' @param bin Minutes per bin; a divisor of a day.
#' @param quantile Share of days the decision line is enough on.
#' @param typical `"median"` or `NULL`.
#' @param shade Shade how often each count was needed.
#' @param days,hours,spans,steps,colors,dimension,key_title As in [hl_lanes()].
#' @param order Group order.
#' @param title,subtitle,caption Frame texts.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' staff <- data.frame(role = "Doctors",
#'                     start = c("2026-01-05 08:00", "2026-01-05 09:00", "2026-01-06 08:30"),
#'                     end = c("2026-01-05 12:00", "2026-01-05 10:00", "2026-01-06 11:00"))
#' hl_levels(staff, "start", end = "end", by = "role")
#' @export
hl_levels <- function(data, time, count = NULL, end = NULL, by = NULL, bin = NULL, quantile = NULL,
                      typical = "median", shade = TRUE, days = NULL, order = NULL, steps = NULL, hours = NULL,
                      spans = NULL, colors = NULL, dimension = NULL, key_title = NULL, title = NULL, subtitle = NULL,
                      caption = NULL, size = "double") {
  check_columns(data, c(time, count, end, by))
  if (is.null(count) == is.null(end)) {
    stop("hairline: levels: give count = (counts at times) or end = (intervals), not both", call. = FALSE)
  }
  if (!is.null(typical) && !identical(typical, "median")) {
    stop(sprintf("hairline: levels: typical '%s' must be 'median' or NULL", typical), call. = FALSE)
  }
  rules <- hl_tokens()$levels
  quantile <- check_quantile(quantile %||% rules$quantile)
  bin <- check_bin(bin %||% hl_tokens()$lanes$bin, "levels")
  steps <- check_steps(steps, "levels")
  hours <- check_hours(hours)
  found <- peaks_per_group(data, time, count, end, by, bin, days, order)
  groups <- found$groups
  names <- names(groups)
  colours <- if (is.null(by)) stats::setNames(lone_colour(), "") else colours_for(names, colors, dimension)
  occupied <- which(Reduce(`|`, lapply(groups, function(peaks) apply(peaks, 2, max) > 0)))
  if (!length(occupied)) stop("hairline: levels: every count is 0 on the days kept; nothing to draw", call. = FALSE)
  bins <- seq(min(occupied), max(occupied))
  cells <- list()
  lines <- list()
  plot <- ggplot2::ggplot() + span_layers(spans)
  for (name in names) {
    peaks <- groups[[name]]
    if (shade) cells[[name]] <- level_cells(name, peaks, bins, colours[[name]], steps, bin)
    lines[[name]] <- level_line_layers(name, peaks, bins, quantile, typical, bin)
  }
  shaded <- do.call(rbind, unname(cells))
  panel_names <- if (is.null(by)) humanise(count %||% word("people")) else names
  facet <- function(frame, name) {
    frame$.panel <- factor(rep(panel_names[match(name, names)], nrow(frame)), levels = panel_names)
    frame
  }
  if (!is.null(shaded)) {
    shaded <- do.call(rbind, lapply(names, function(name) if (!is.null(cells[[name]])) facet(cells[[name]], name)))
    plot <- plot + ggplot2::geom_rect(data = shaded, ggplot2::aes(xmin = .data$x0, xmax = .data$x1, ymin = .data$y0,
                                                                  ymax = .data$y1, fill = .data$fill), colour = NA) +
      ggplot2::scale_fill_identity()
  }
  for (name in names) {
    for (layer in lines[[name]]$layers) {
      layer$data <- facet(layer$data, name)
      plot <- plot + layer
    }
  }
  tallest <- max(vapply(groups, max, 0))
  # Each panel from half a level below 0 to half a level above its own highest count.
  reach <- do.call(rbind, lapply(names, function(name) {
    facet(data.frame(y = c(-0.5, max(max(groups[[name]]), 1) + 0.5)), name)
  }))
  plot <- plot + ggplot2::geom_blank(data = reach, ggplot2::aes(y = .data$y))
  share <- hl_format_percent(quantile, 0)
  items <- c(list(list(kind = "line", colour = hl_settings()$neutral$ink, label = word("decision", share = share))),
             if (!is.null(typical)) list(list(kind = "dash", colour = hl_settings()$neutral$muted,
                                              label = word("typical_line"))))
  plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.panel), ncol = 1, scales = "free_y") +
    integer_scale() +
    time_scale(time_window(list(time_meta(hours, (bins[1] - 1) * bin / 60, bins[length(bins)] * bin / 60, spans)))) +
    ggplot2::labs(title = title %||% paste(humanise(count %||% "people"), "over the day"),
                  subtitle = joined_subtitle(subtitle, found$label),
                  caption = with_caption(caption, word("levels_note")), x = NULL, y = NULL) + theme_hairline() +
    hl_legend(c(span_items(spans), items))
  for (name in names) {
    stats <- c(hl_format_number(max(lines[[name]]$decision), 0),
               if (!is.null(typical)) hl_format_number(max(lines[[name]]$middle), 0))
    names(stats) <- c(word("up_to"), if (!is.null(typical)) word("typical"))
    plot <- plot + hl_panel_header(panel = panel_names[match(name, names)], stats = stats, key = word("up_to"))
  }
  if (shade) {
    key <- if (length(colours) == 1) step_colours(colours[[1]], length(steps)) else step_colours(NULL, length(steps))
    plot <- plot + hl_legend_ramp(key, steps, key_title %||% word("share_of_days"))
  }
  plot@meta$hairline_hover <- if (!is.null(shaded)) {
    cbind(panel = match(as.character(shaded$.panel), panel_names),
          shaded[, c("name", "colour", "x0", "y0", "x1", "y1", "text")])
  }
  plot@meta$hairline_time <- list(time_meta(hours, (bins[1] - 1) * bin / 60, bins[length(bins)] * bin / 60, spans))
  plot@meta$hairline_row_notes <- c(word("levels_note"), paste0(found$label, "."))
  plot@meta$hairline_min_plot <- length(groups) * max(tallest + 1, rules$min_rows) * rules$row_pitch
  plot@meta$hairline_height_mm <- 40
  plot@meta$hairline_size <- size
  plot
}
