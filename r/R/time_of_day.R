# The time of day, shared by hl_lanes(), hl_levels() and hl_swimlanes(): clock hours from dates, the calendar filter,
# bins over the day, intervals per day and the first-free assignment of tasks to people; then the drawing helpers the
# three share (binned colours, row blocks, the time-of-day scale). The same rules as the time-of-day helpers of the
# Python package.

day_minutes <- 1440
day_names <- c("weekdays", "weekends")

# Dates and times (or ISO text) as moments in UTC with the data's own clock times; anything else is refused with the
# column named.
as_times <- function(values, column, chart) {
  if (inherits(values, "POSIXct")) {
    return(as.POSIXct(format(values, "%Y-%m-%d %H:%M:%OS6"), tz = "UTC", format = "%Y-%m-%d %H:%M:%OS"))
  }
  if (inherits(values, "Date")) return(as.POSIXct(format(values), tz = "UTC"))
  parsed <- tryCatch(study_iso_dates(values, column), error = function(error) NULL)
  if (inherits(parsed, "Date")) parsed <- as.POSIXct(format(parsed), tz = "UTC")
  if (is.null(parsed) || sum(!is.na(parsed)) != sum(!is.na(values))) {
    first <- values[!is.na(values)][1]
    stop(sprintf("hairline: %s: '%s' needs dates with times (2026-03-02 07:15); got '%s'", chart, column, first),
         call. = FALSE)
  }
  parsed
}

# Hours since midnight: numbers as they are (7.25), "HH:MM" text, or the time of a date (07:15 is 7.25).
clock_hours <- function(values, column, chart) {
  if (is.numeric(values) && !inherits(values, c("Date", "POSIXt"))) return(as.numeric(values))
  text <- as.character(values)
  if (all(grepl("^[0-9]{1,2}:[0-9]{2}$", text))) {
    parts <- do.call(rbind, strsplit(text, ":", fixed = TRUE))
    return(as.numeric(parts[, 1]) + as.numeric(parts[, 2]) / 60)
  }
  times <- as_times(values, column, chart)
  as.numeric(times - as.POSIXct(format(times, "%Y-%m-%d"), tz = "UTC"), units = "hours")
}

check_bin <- function(bin, chart) {
  whole <- is.numeric(bin) && length(bin) == 1 && is.finite(bin) && bin >= 1 && bin == round(bin)
  if (!whole || day_minutes %% bin != 0) {
    stop(sprintf(paste("hairline: %s: bin must be a whole number of minutes that divides a day (5, 10, 15, 30, 60);",
                       "got %s"), chart, paste(format(bin), collapse = ", ")), call. = FALSE)
  }
  as.integer(bin)
}

day_start <- function(times) as.POSIXct(format(min(times), "%Y-%m-%d"), tz = "UTC")

day_count <- function(starts, ends) {
  as.integer(difftime(as.Date(format(max(ends), "%Y-%m-%d")), as.Date(format(min(starts), "%Y-%m-%d")),
                      units = "days")) + 1L
}

# The days from the first to the last in the data, kept by the calendar filter: NULL (all), "weekdays", "weekends", or
# dates; their offsets from the first day, and the filter's name with its n for the subtitle ("Weekdays, 128 days").
calendar <- function(origin, total, days, chart) {
  every <- as.Date(format(origin, "%Y-%m-%d")) + seq_len(total) - 1
  weekday <- as.integer(format(every, "%u"))
  name <- NULL
  if (is.null(days)) {
    kept <- every
    name <- word("all_days")
  } else if (is.character(days) && length(days) == 1 && !grepl("^[0-9]{4}-", days)) {
    if (!days %in% day_names) {
      stop(sprintf("hairline: %s: days '%s' must be 'weekdays', 'weekends' or dates", chart, days), call. = FALSE)
    }
    kept <- if (days == "weekdays") every[weekday <= 5] else every[weekday >= 6]
    name <- word(days)
  } else {
    kept <- unique(as.Date(days))
    outside <- kept[!kept %in% every]
    if (length(outside)) {
      stop(sprintf("hairline: %s: days names %s, which the data does not cover (%s to %s)", chart, format(outside[1]),
                   format(every[1]), format(every[length(every)])), call. = FALSE)
    }
  }
  if (!length(kept)) {
    stop(sprintf("hairline: %s: the calendar filter keeps no day of the data", chart), call. = FALSE)
  }
  count <- word("days", n = hl_format_number(length(kept), 0))
  list(rows = as.integer(kept - every[1]), label = if (is.null(name)) count else paste0(name, ", ", count))
}

# Intervals at the same time, minute by minute from `origin` over `total` days (an interval covers the minutes it
# touches; one that crosses midnight runs on into the next day).
minute_counts <- function(starts, ends, origin, total) {
  minutes <- total * day_minutes
  begin <- floor(as.numeric(starts - origin, units = "mins") + 1e-9)
  finish <- ceiling(as.numeric(ends - origin, units = "mins") - 1e-9)
  begin <- pmin(pmax(begin, 0), minutes)
  finish <- pmin(pmax(pmax(finish, begin + 1), 0), minutes)
  delta <- tabulate(begin + 1, minutes + 1) - tabulate(finish + 1, minutes + 1)
  cumsum(delta)[seq_len(minutes)]
}

# Minute values as a days x bins matrix: the peak in each bin, or whether any minute is above zero.
binned <- function(minutes, bin, how) {
  shaped <- matrix(minutes, nrow = bin)
  peaks <- do.call(pmax, lapply(seq_len(bin), function(row) shaped[row, ]))
  peaks <- matrix(peaks, ncol = day_minutes / bin, byrow = TRUE)
  if (how == "peak") peaks else (peaks > 0) * 1
}

interval_rows <- function(data, start, end, chart) {
  starts <- as_times(data[[start]], start, chart)
  ends <- as_times(data[[end]], end, chart)
  backwards <- which(ends < starts)
  if (length(backwards)) {
    stop(sprintf("hairline: %s: row %d ends before it starts (%s to %s)", chart, backwards[1],
                 format(starts[backwards[1]]), format(ends[backwards[1]])), call. = FALSE)
  }
  list(starts = starts, ends = ends)
}

# The hours with data plus a margin, on whole hours: 06 to 22 rather than a night of nothing.
hour_window <- function(lows, highs, margin) {
  c(max(0, floor(min(lows) + hour_noise) - margin), min(48, ceiling(max(highs) - hour_noise) + margin))
}

# Float noise a data limit may carry, which must not add an hour to the window.
hour_noise <- 1e-9

# Each task to the first person free at its start, people numbered from 1 in the order they are needed; tasks in
# order of start (then end), so the result is the least number of people the tasks need.
first_free <- function(starts, ends) {
  free_at <- numeric()
  people <- integer(length(starts))
  for (index in order(starts, ends, seq_along(starts))) {
    person <- which(free_at <= starts[index])[1]
    if (is.na(person)) {
      free_at <- c(free_at, ends[index])
      person <- length(free_at)
    } else {
      free_at[person] <- ends[index]
    }
    people[index] <- person
  }
  people
}

# `count` colours of one hue from light to dark (the ramp of a group's colour, or greys), its near-white first step
# left out so the lightest bin still reads on the surface.
step_colours <- function(base, count) {
  hue <- if (is.null(base)) NULL else hex_to_oklch(base)[3]
  interpolate_colors(sequential_ramp(hue), count + 1)[-1]
}

# The bin of a value: the first step it does not exceed (the last for anything above).
step_index <- function(value, steps) {
  found <- which(value <= steps + 1e-12)
  if (length(found)) found[1] else length(steps)
}

check_steps <- function(steps, chart) {
  found <- as.numeric(steps %||% unlist(hl_tokens()$legend_ramp$steps))
  if (!length(found) || any(!(found > 0 & found <= 1)) || is.unsorted(found, strictly = TRUE)) {
    stop(sprintf("hairline: %s: steps must rise within (0, 1], such as c(0.25, 0.5, 0.75, 1); got %s", chart,
                 paste(format(steps), collapse = ", ")), call. = FALSE)
  }
  found
}

# A row's label inside its block: "Theatre 2" in block "Theatre" reads "2"; other names stay whole.
short_label <- function(name, block) {
  rest <- trimws(substring(name, nchar(block) + 1))
  if (nzchar(block) && startsWith(name, block) && nzchar(rest)) rest else name
}

# Blocks for the frame (name, colour, count, labels), each row's y (top row highest) and each row's colour (its
# group's).
row_layout <- function(rows, groups, palette, lone) {
  groups <- groups %||% rep("", length(rows))
  blocks <- list()
  colours <- stats::setNames(vapply(groups, function(group) {
    if (group %in% names(palette)) unname(palette[[group]]) else lone
  }, character(1)), rows)
  for (index in seq_along(rows)) {
    label <- short_label(rows[index], groups[index])
    last <- length(blocks)
    if (last && identical(blocks[[last]]$name, groups[index])) {
      blocks[[last]]$labels <- c(blocks[[last]]$labels, label)
      blocks[[last]]$count <- blocks[[last]]$count + 1
    } else {
      blocks[[last + 1]] <- list(name = groups[index], colour = unname(colours[index]), count = 1, labels = label)
    }
  }
  list(blocks = blocks, ys = stats::setNames(length(rows) - seq_along(rows), rows), colours = colours)
}

hour_span <- function(bin_index, bin) {
  start <- bin_index * bin / 60
  c(start, start + bin / 60)
}

clock <- function(hours) clock_text(hours)

# Whole hours in [low, high] at the smallest step of `time_axis.steps` that gives at most `target` ticks.
hour_breaks <- function(low, high, target) {
  for (step in unlist(hl_tokens()$time_axis$steps)) {
    first <- ceiling(low / step) * step
    breaks <- if (first <= floor(high)) seq(first, floor(high), by = step) else numeric()
    if (length(breaks) <= target) return(breaks)
  }
  c(low, high)
}

# "06", "18", and past midnight "02" again.
hour_label <- function(values) sprintf("%02d", as.integer(round(values)) %% 24L)

# Whole-number ticks from the lowest to the highest whole number in range, at most six of them.
integer_breaks <- function(low, high) {
  first <- ceiling(low - 1e-9)
  last <- floor(high + 1e-9)
  step <- c(1, 2, 5, 10, 20, 50, 100, 200, 500, 1000)
  step <- step[(last - first) / step <= 5][1]
  seq(first, last, by = step)
}

# The time-of-day x scale: hour labels, the window given, data outside it kept for the layers.
time_scale <- function(window, columns = 1) {
  target <- if (columns == 1) hl_tokens()$time_axis$target else if (columns == 2) 5 else 4
  breaks <- hour_breaks(window[1], window[2], target)
  scale <- ggplot2::scale_x_continuous(limits = window, breaks = breaks, labels = hour_label(breaks),
                                       expand = c(0, 0), oob = function(x, ...) x)
  scale$hairline <- list(time = TRUE, target_given = TRUE)
  scale
}

# A y scale on whole numbers only (counts of people or places): no 1.5 people on the axis. Each panel's range comes
# from its data (a chart adds the reach it wants).
integer_scale <- function() {
  scale <- ggplot2::scale_y_continuous(breaks = function(limits) integer_breaks(limits[1], limits[2]),
                                       labels = function(values) vapply(values, hl_format_number, "", digits = 0),
                                       expand = c(0, 0))
  scale$hairline <- list(digits = 0, target_given = TRUE)
  scale
}

# Rows by number on a y scale, top row first, with the panel's extra room on neither side.
row_scale <- function(labels) {
  count <- length(labels)
  ggplot2::scale_y_continuous(breaks = seq_len(count) - 1, labels = rev(labels), limits = c(-0.5, count - 0.5),
                              expand = c(0, 0))
}

# A hairline between row blocks.
separator_layer <- function(blocks) {
  if (length(blocks) < 2) return(list())
  counts <- vapply(blocks, `[[`, numeric(1), "count")
  positions <- sum(counts) - 0.5 - cumsum(counts)[-length(counts)]
  settings <- hl_settings()
  layer <- ggplot2::geom_hline(yintercept = positions, colour = settings$neutral$axis,
                               linewidth = pt_to_linewidth(hl_tokens()$reference$width * settings$base_size))
  layer$hairline_fixed <- TRUE
  list(layer)
}

# Named periods shaded behind the data ({"Regular hours": c(7, 16)}), each with a legend item.
span_layers <- function(spans) {
  if (!length(spans)) return(list())
  band <- hl_settings()$neutral$band
  frame <- data.frame(xmin = vapply(spans, `[`, numeric(1), 1), xmax = vapply(spans, `[`, numeric(1), 2))
  list(static_layer(ggplot2::geom_rect(data = frame, ggplot2::aes(xmin = .data$xmin, xmax = .data$xmax),
                                       ymin = -Inf, ymax = Inf, fill = band, colour = NA, inherit.aes = FALSE)))
}

span_items <- function(spans) {
  band <- hl_settings()$neutral$band
  lapply(names(spans), function(name) list(kind = "band", colour = band, label = name))
}

check_hours <- function(hours) {
  if (is.null(hours)) return(NULL)
  if (!(length(hours) == 2 && hours[1] >= 0 && hours[1] < hours[2] && hours[2] <= 48)) {
    stop(sprintf("hairline: time_axis: hours must run from low to high within 0 to 48; got %s",
                 paste(format(hours), collapse = ", ")), call. = FALSE)
  }
  as.numeric(hours)
}

# What a composition needs to share one time axis: the hours given, or the data's extent.
time_meta <- function(hours, lows, highs, spans) {
  span_ends <- unlist(spans)
  list(hours = hours, low = min(c(lows, span_ends)), high = max(c(highs, span_ends)))
}

# The hours a time-of-day chart shows: those given, else its data plus a margin.
time_window <- function(times) {
  given <- Filter(Negate(is.null), lapply(times, `[[`, "hours"))
  if (length(given)) return(c(min(vapply(given, `[`, 0, 1)), max(vapply(given, `[`, 0, 2))))
  hour_window(vapply(times, `[[`, 0, "low"), vapply(times, `[[`, 0, "high"), hl_tokens()$time_axis$margin_hours)
}

# The subtitle with the calendar filter's name after it ("Weekdays, 130 days").
joined_subtitle <- function(subtitle, label) {
  parts <- c(subtitle, label)
  if (length(parts)) paste(parts, collapse = " \u00b7 ") else NULL
}

# The caption note a chart adds when drawn into a composition, once.
add_notes <- function(caption, notes) {
  for (note in notes) if (!grepl(note, caption %||% "", fixed = TRUE)) caption <- with_caption(caption, note)
  caption
}
