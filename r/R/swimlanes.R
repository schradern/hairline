# Swimlanes for one day, mirroring the Python swimlanes(): a bar per interval in its row (which patient is where,
# which person covers them), the label inside when it fits, an inner interval as a darker band along its lower edge
# (the narcosis within the stay), rows in named blocks and the time-of-day axis; tasks can be given to the first free
# person.

swimlane_assign <- c("first_free")
# How much darker the inner interval is drawn, in OKLCH lightness.
inner_darker <- 0.22

# Each column as hours since midnight of the first day: numbers as they are, dates relative to that day (a stay past
# midnight reads 25.5). `optional` columns may be missing in a row (no inner interval there).
day_hours <- function(data, columns, optional = character()) {
  found <- list()
  times <- list()
  for (column in columns) {
    values <- data[[column]]
    if (is.numeric(values) && !inherits(values, c("Date", "POSIXt"))) {
      found[[column]] <- as.numeric(values)
      next
    }
    present <- if (column %in% optional) !is.na(values) & nzchar(as.character(values)) else rep(TRUE, length(values))
    parsed <- rep(as.POSIXct(NA, tz = "UTC"), length(values))
    if (any(present)) parsed[present] <- as_times(values[present], column, "swimlanes")
    times[[column]] <- parsed
  }
  if (length(times)) {
    origin <- day_start(do.call(c, lapply(times, function(value) value[!is.na(value)])))
    for (column in names(times)) found[[column]] <- as.numeric(times[[column]] - origin, units = "hours")
  }
  found
}

# Rows named by person: within each group, each task to the first person free at its start (1, 2, ...).
assigned_rows <- function(data, group, hours, start, end) {
  labels <- if (is.null(group)) rep("", nrow(data)) else as.character(data[[group]])
  people <- character(nrow(data))
  for (name in unique(labels)) {
    mask <- labels == name
    people[mask] <- trimws(paste(name, first_free(hours[[start]][mask], hours[[end]][mask])))
  }
  people
}

darker <- function(colour) {
  lch <- hex_to_oklch(colour)
  oklch_to_hex(max(0, lch[1] - inner_darker), lch[2], lch[3])
}

#' Swimlanes for one day
#'
#' One bar per interval (`start` to `end`: hours, or dates with times on one
#' day) in its `row`, coloured by `color_by` (the legend lists its values; else
#' by `group`), `label` inside the bar where it fits. `inner` names the start
#' and end columns of an inner interval, drawn as a darker band along the bar's
#' lower edge. `group` draws the rows as blocks (places, doctors, nurses), the
#' name once in its colour. `assign = "first_free"` turns a list of tasks into
#' rows of people: within each group, each task goes to the first person free
#' at its start.
#'
#' @param data A data frame.
#' @param row Column naming each bar's row; `NULL` with `assign = "first_free"`.
#' @param start,end Columns with each interval's start and end.
#' @param label Column with the text inside each bar.
#' @param color_by Column the bars are coloured by.
#' @param inner Start and end columns of an inner interval.
#' @param group Column whose values draw the rows as named blocks.
#' @param assign `"first_free"` to make rows of people from tasks, or `NULL`.
#' @param order Row order.
#' @param hours,spans,colors,dimension As in [hl_lanes()].
#' @param title,subtitle,caption Frame texts.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' day <- data.frame(place = c("Theatre 1", "Theatre 1", "Recovery 1"), patient = c("P1", "P2", "P1"),
#'                   start = c(8, 10.5, 10), end = c(10, 12, 11.2))
#' hl_swimlanes(day, "place", "start", "end", label = "patient")
#' @export
hl_swimlanes <- function(data, row, start, end, label = NULL, color_by = NULL, inner = NULL, group = NULL,
                         assign = NULL, order = NULL, hours = NULL, spans = NULL, colors = NULL, dimension = NULL,
                         title = NULL, subtitle = NULL, caption = NULL, size = "double") {
  if (!is.null(assign) && !identical(assign, "first_free")) {
    stop(sprintf("hairline: swimlanes: assign '%s' must be 'first_free' or NULL", assign), call. = FALSE)
  }
  if (is.null(row) && is.null(assign)) {
    stop("hairline: swimlanes: give row =, or assign = \"first_free\" to make rows of people", call. = FALSE)
  }
  if (!is.null(inner) && length(inner) != 2) {
    stop(sprintf("hairline: swimlanes: inner takes c(start, end) columns; got %s", paste(inner, collapse = ", ")),
         call. = FALSE)
  }
  columns <- c(start, end, inner)
  check_columns(data, c(row, label, color_by, group, columns))
  hours_of <- day_hours(data, columns, inner %||% character())
  backwards <- which(hours_of[[end]] < hours_of[[start]])
  if (length(backwards)) stop(sprintf("hairline: swimlanes: row %d ends before it starts", backwards[1]), call. = FALSE)
  data$.row <- if (!is.null(assign)) assigned_rows(data, group, hours_of, start, end) else as.character(data[[row]])
  check_labels(data, c(group, color_by), "swimlanes")
  rows <- ordered_names(data$.row, order, "swimlanes", row %||% "row")
  groups <- NULL
  if (!is.null(group)) {
    owner <- as.character(data[[group]])[match(rows, data$.row)]
    rows <- unlist(lapply(unique(owner), function(block) rows[owner == block]))
    groups <- as.character(data[[group]])[match(rows, data$.row)]
  }
  coloured <- color_by %||% group
  names <- if (is.null(coloured)) character() else unique(as.character(data[[coloured]]))
  palette <- if (length(names)) colours_for(names, colors, dimension) else character()
  settings <- hl_settings()
  layout <- row_layout(rows, groups, if (!is.null(group) && is.null(color_by)) palette else character(), lone_colour())
  if (!is.null(color_by) && !is.null(group)) {
    # Colour already means `color_by`: the block names stay in ink.
    layout$blocks <- lapply(layout$blocks, function(block) {
      block$colour <- settings$neutral$ink
      block
    })
  }
  rules <- hl_tokens()$swimlanes
  half <- rules$bar / 2
  colours <- if (is.null(coloured)) rep(lone_colour(), nrow(data)) else unname(palette[as.character(data[[coloured]])])
  bars <- data.frame(x0 = hours_of[[start]], x1 = hours_of[[end]], y = unname(layout$ys[data$.row]), fill = colours)
  texts <- if (is.null(label)) rep("", nrow(data)) else as.character(data[[label]])
  plot <- ggplot2::ggplot() + span_layers(spans) +
    ggplot2::geom_rect(data = bars, ggplot2::aes(xmin = .data$x0, xmax = .data$x1, ymin = .data$y - half,
                                                 ymax = .data$y + half, fill = .data$fill),
                       colour = settings$neutral$surface, linewidth = pt_to_linewidth(rules$gap_pt))
  if (!is.null(inner)) {
    inside <- data.frame(x0 = hours_of[[inner[1]]], x1 = hours_of[[inner[2]]], y = bars$y,
                         fill = vapply(colours, darker, ""))
    inside <- inside[is.finite(inside$x0) & is.finite(inside$x1), , drop = FALSE]
    plot <- plot + ggplot2::geom_rect(data = inside, ggplot2::aes(xmin = .data$x0, xmax = .data$x1,
                                                                  ymin = .data$y - half,
                                                                  ymax = .data$y - half + rules$inner * 2 * half,
                                                                  fill = .data$fill), colour = NA)
  }
  time <- time_meta(check_hours(hours), min(bars$x0), max(bars$x1), spans)
  labels <- if (is.null(groups)) rows else unlist(lapply(layout$blocks, `[[`, "labels"))
  plot <- plot + ggplot2::scale_fill_identity() + (if (!is.null(groups)) separator_layer(layout$blocks)) +
    row_scale(labels) + time_scale(time_window(list(time))) +
    ggplot2::labs(title = title %||% paste(humanise(row %||% "tasks"), "over the day"), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline() +
    hl_legend(if (!is.null(color_by)) lapply(names, function(name) {
      list(kind = "square", colour = unname(palette[[name]]), label = name)
    }) else list())
  style <- list(neutral = settings$neutral)
  plot@meta$hairline_blocks <- if (!is.null(groups)) list(layout$blocks)
  plot@meta$hairline_inside <- lapply(which(nzchar(texts)), function(index) {
    list(panel = 1L, start = bars$x0[index], end = bars$x1[index], y = bars$y[index], text = texts[index],
         colour = contrast_text(colours[index], style))
  })
  prefix <- ifelse(nzchar(texts), paste0(texts, " \u00b7 "), "")
  plot@meta$hairline_hover <- data.frame(panel = 1L, name = data$.row, colour = colours, x0 = bars$x0,
                                         y0 = bars$y - half, x1 = bars$x1, y1 = bars$y + half,
                                         text = paste0(prefix, data$.row, ": ", clock(bars$x0), "\u2013",
                                                       clock(bars$x1)))
  plot@meta$hairline_time <- list(time)
  plot@meta$hairline_min_plot <- length(rows) * rules$row_pitch
  plot@meta$hairline_height_mm <- 40
  plot@meta$hairline_size <- size
  plot
}
