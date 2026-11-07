# Lanes over the time of day, mirroring the Python lanes(): one row per place, the time of day across, each cell
# coloured by the share of days the place was occupied then, in its group's ramp, binned as the legend row's key; moves
# between places as faint connectors in the gaps between rows.

lane_values <- c("share", "count")
flow_columns <- c("from", "to", "time")

# Rows top to bottom: by group (in data order), then in `order` or data order within it.
lane_rows <- function(data, row, group, order) {
  check_labels(data, c(row, group), "lanes")
  names <- ordered_names(data[[row]], order, "lanes", row)
  if (is.null(group)) return(list(rows = names, groups = NULL))
  owners <- lapply(names, function(name) unique(as.character(data[[group]][as.character(data[[row]]) == name])))
  split <- which(lengths(owners) > 1)
  if (length(split)) {
    stop(sprintf("hairline: lanes: row '%s' belongs to more than one %s: %s", names[split[1]], group,
                 paste(owners[[split[1]]], collapse = ", ")), call. = FALSE)
  }
  owner <- vapply(owners, `[`, "", 1)
  rows <- unlist(lapply(unique(owner), function(block) names[owner == block]))
  list(rows = rows, groups = owner[match(rows, names)])
}

# Per row the value per bin of the day over the days kept: the share of days occupied, or the mean number of
# intervals at the same time.
interval_matrix <- function(data, rows, row, start, end, bin, days, value) {
  times <- interval_rows(data, start, end, "lanes")
  origin <- day_start(times$starts)
  total <- day_count(times$starts, times$ends)
  kept <- calendar(origin, total, days, "lanes")
  names <- as.character(data[[row]])
  matrix <- lapply(rows, function(name) {
    mask <- names == name
    cells <- binned(minute_counts(times$starts[mask], times$ends[mask], origin, total), bin,
                    if (value == "share") "any" else "peak")
    colMeans(cells[kept$rows + 1, , drop = FALSE])
  })
  list(matrix = stats::setNames(matrix, rows), label = kept$label, days = length(kept$rows))
}

# A precomputed share per row and bin start (07:15 or 7.25): each value in its bin of the day.
share_matrix <- function(data, rows, row, start, amount, bin) {
  bins <- floor(clock_hours(data[[start]], start, "lanes") * 60 / bin + 1e-9) %% (day_minutes / bin)
  names <- as.character(data[[row]])
  values <- as.numeric(data[[amount]])
  values[is.na(values)] <- 0
  stats::setNames(lapply(rows, function(name) {
    cells <- numeric(day_minutes / bin)
    mask <- names == name
    for (index in which(mask)) cells[bins[index] + 1] <- max(cells[bins[index] + 1], values[index])
    cells
  }), rows)
}

# One connector per (from, to, bin) between the two rows, its opacity the moves per day against the reference (the
# busiest connector by default), rare ones below the floor left out.
flow_segments <- function(flows, columns, layout, rows, bin, days, reference, floor) {
  check_columns(flows, columns)
  named <- unique(c(as.character(flows[[columns[1]]]), as.character(flows[[columns[2]]])))
  unknown <- sort(setdiff(named, rows))
  if (length(unknown)) {
    stop(sprintf("hairline: lanes: flows name '%s', which is not a row; rows: %s", unknown[1],
                 paste(rows, collapse = ", ")), call. = FALSE)
  }
  bins <- floor(clock_hours(flows[[columns[3]]], columns[3], "lanes") * 60 / bin + 1e-9)
  keys <- combination_key(flows[[columns[1]]], flows[[columns[2]]], bins)
  first <- !duplicated(keys)
  moves <- data.frame(from = as.character(flows[[columns[1]]][first]), to = as.character(flows[[columns[2]]][first]),
                      bin = bins[first], rate = as.numeric(table(factor(keys, levels = keys[first]))) / days)
  reference <- reference %||% max(moves$rate)
  floor <- floor %||% (hl_tokens()$lanes$flow_floor * reference)
  moves <- moves[moves$rate >= floor & moves$from != moves$to, , drop = FALSE]
  data.frame(x = (moves$bin + 0.5) * bin / 60, y = unname(layout$ys[moves$from]), yend = unname(layout$ys[moves$to]),
             colour = unname(layout$colours[moves$to]), alpha = pmin(1, moves$rate / reference))
}

# Rectangles per occupied bin, coloured by the bin of their value; each a tooltip target.
lane_cells <- function(matrix, layout, ramps, steps, bin, value, top) {
  half <- hl_tokens()$lanes$cell / 2
  cells <- list()
  for (name in names(matrix)) {
    occupied <- which(matrix[[name]] > 0)
    if (!length(occupied)) next
    amounts <- matrix[[name]][occupied]
    low <- (occupied - 1) * bin / 60
    high <- low + bin / 60
    y <- layout$ys[[name]]
    colour <- layout$colours[[name]]
    shown <- if (value == "share") vapply(amounts, hl_format_percent, "", digits = 0) else
      vapply(amounts, hl_format_number, "", digits = 1)
    cells[[name]] <- data.frame(name = name, colour = colour, x0 = low, x1 = high, y0 = y - half, y1 = y + half,
                                fill = ramps[[colour]][vapply(amounts / top, step_index, 1, steps = steps)],
                                text = paste0(name, ", ", clock(low), "\u2013", clock(high), ": ", shown))
  }
  do.call(rbind, unname(cells))
}

#' Lanes over the time of day
#'
#' One row per place over the time of day, from intervals (`start` and `end`,
#' dates with times) per `row`. Each `bin`-minute cell shows the share of days
#' the place was occupied then (`value = "share"`), or the mean number of
#' intervals at once (`value = "count"`), in the colour of the row's `group`,
#' binned at `steps` as the key in the legend row shows. `group` draws the rows
#' as blocks: its name once in its colour, the rows by number. Without `end`,
#' `start` holds each cell's time of day and `amount` its precomputed share.
#'
#' `flows` (a data frame of from, to and time; `flow_columns` names them) adds
#' the moves between rows: one faint connector per pair and bin, stronger the
#' more moves per day, in the colour of the row moved to. Combine with
#' [hl_levels()] in [hl_rows()] to put cause above effect on one time axis.
#'
#' @param data A data frame.
#' @param row,start,end Columns: the place, the start and end of each interval.
#' @param group Column whose values draw the rows as named blocks and give their colours.
#' @param bin Minutes per cell; a divisor of a day.
#' @param value `"share"` of days occupied or mean `"count"` at once.
#' @param days Calendar filter: `"weekdays"`, `"weekends"` or dates; named with its n in the subtitle.
#' @param amount Column with a precomputed share per cell, when `end` is not given.
#' @param order Row order within the blocks.
#' @param flows,flow_columns Moves between rows and the names of their from, to and time columns.
#' @param flow_reference,flow_floor Moves per day that draw a connector at full strength, and the fewest drawn.
#' @param steps The key's bins, shares within (0, 1].
#' @param hours The hours shown, e.g. `c(6, 22)`; by default the hours with data and a margin.
#' @param spans Named periods to shade, e.g. `list("Regular hours" = c(7, 16))`.
#' @param colors Named colours for this chart only.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param dimension What the groups are, so their colours keep off the slots another dimension holds.
#' @param key_title Title of the key (default: the locale's "Share of days").
#' @param title,subtitle,caption Frame texts.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' stays <- data.frame(place = c("Theatre 1", "Theatre 1", "Recovery 1"),
#'                     section = c("Theatre", "Theatre", "Recovery"),
#'                     start = c("2026-01-05 08:00", "2026-01-06 09:10", "2026-01-05 10:05"),
#'                     end = c("2026-01-05 10:00", "2026-01-06 11:30", "2026-01-05 11:20"))
#' hl_lanes(stays, "place", "start", "end", group = "section")
#' @export
hl_lanes <- function(data, row, start, end = NULL, group = NULL, bin = NULL, value = "share", days = NULL,
                     amount = NULL, order = NULL, flows = NULL, flow_columns = c("from", "to", "time"),
                     flow_reference = NULL, flow_floor = NULL, steps = NULL, hours = NULL, spans = NULL,
                     colors = NULL, dimension = NULL, key_title = NULL, title = NULL, subtitle = NULL, caption = NULL,
                     size = "double") {
  if (!value %in% lane_values) {
    stop(sprintf("hairline: lanes: value '%s' must be one of %s", value, paste(lane_values, collapse = ", ")),
         call. = FALSE)
  }
  check_columns(data, c(row, start, end, group, amount))
  if (is.null(end) && is.null(amount)) {
    stop("hairline: lanes: give end = (intervals) or amount = (a precomputed share per cell)", call. = FALSE)
  }
  bin <- check_bin(bin %||% hl_tokens()$lanes$bin, "lanes")
  steps <- check_steps(steps, "lanes")
  hours <- check_hours(hours)
  placed <- lane_rows(data, row, group, order)
  rows <- placed$rows
  found <- if (!is.null(end)) interval_matrix(data, rows, row, start, end, bin, days, value) else
    list(matrix = share_matrix(data, rows, row, start, amount, bin), label = NULL, days = 1)
  top <- if (value == "share") 1 else max(unlist(found$matrix))
  if (!(top > 0)) top <- 1
  palette <- if (is.null(placed$groups)) character() else colours_for(unique(placed$groups), colors, dimension)
  layout <- row_layout(rows, placed$groups, palette, lone_colour())
  ramps <- stats::setNames(lapply(unique(layout$colours), step_colours, count = length(steps)), unique(layout$colours))
  cells <- lane_cells(found$matrix, layout, ramps, steps, bin, value, top)
  if (is.null(cells)) stop("hairline: lanes: no row is occupied in any bin of the days kept", call. = FALSE)
  segments <- if (!is.null(flows)) {
    flow_segments(flows, flow_columns, layout, rows, bin, max(found$days, 1), flow_reference, flow_floor)
  }
  settings <- hl_settings()
  plot <- ggplot2::ggplot() + span_layers(spans)
  if (!is.null(segments) && nrow(segments)) {
    plot <- plot + ggplot2::geom_segment(data = segments, ggplot2::aes(x = .data$x, xend = .data$x, y = .data$y,
                                                                       yend = .data$yend, colour = .data$colour,
                                                                       alpha = .data$alpha),
                                         linewidth = pt_to_linewidth(hl_tokens()$lanes$flow_width *
                                                                       settings$base_size)) +
      ggplot2::scale_colour_identity() + ggplot2::scale_alpha_identity()
  }
  labels <- if (is.null(placed$groups)) rows else unlist(lapply(layout$blocks, `[[`, "labels"))
  time <- time_meta(hours, c(cells$x0, segments$x), c(cells$x1, segments$x), spans)
  plot <- plot + ggplot2::geom_rect(data = cells, ggplot2::aes(xmin = .data$x0, xmax = .data$x1, ymin = .data$y0,
                                                               ymax = .data$y1, fill = .data$fill), colour = NA) +
    ggplot2::scale_fill_identity() + (if (!is.null(placed$groups)) separator_layer(layout$blocks)) +
    row_scale(labels) + time_scale(time_window(list(time))) +
    ggplot2::labs(title = title %||% paste(humanise(row), "over the day"),
                  subtitle = joined_subtitle(subtitle, found$label),
                  caption = caption, x = NULL, y = NULL) + theme_hairline() +
    hl_legend(c(span_items(spans), if (!is.null(flows)) {
      list(list(kind = "line", colour = settings$neutral$muted, label = word("move")))
    }))
  key <- if (length(ramps) == 1) ramps[[1]] else step_colours(NULL, length(steps))
  plot <- plot + hl_legend_ramp(key, steps * top, key_title %||% word("share_of_days"),
                                if (value == "share") "percent" else "number", c(0, top))
  plot@meta$hairline_blocks <- if (!is.null(placed$groups)) list(layout$blocks)
  plot@meta$hairline_hover <- cbind(panel = 1L, cells[, c("name", "colour", "x0", "y0", "x1", "y1", "text")])
  plot@meta$hairline_time <- list(time)
  plot@meta$hairline_row_notes <- if (!is.null(found$label)) paste0(found$label, ".")
  plot@meta$hairline_min_plot <- length(rows) * hl_tokens()$lanes$row_pitch
  plot@meta$hairline_height_mm <- 40
  plot@meta$hairline_size <- size
  plot
}
