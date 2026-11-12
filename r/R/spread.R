# Spread rows, mirroring the Python spread(): per group the range as a thin line, the interquartile range as a band
# in the group's colour, the median as a dot, an optional reference tick, and the key numbers on the right (or, on
# a figure too narrow for both, on a line under each row).

spread_stats <- c("median", "iqr", "mean", "n", "range", "levels", "sd", "ci")
spread_default_summary <- c("median", "iqr", "range")

# Key numbers as (label, value) pairs, drawn like a panel header's key numbers, the group's mark last.
spread_pairs <- function(values, stats, numbers, mark, mark_label, discrete = FALSE) {
  pairs <- stat_pairs(values, stats, numbers, discrete)
  if (!is.null(mark) && !is.null(mark_label)) pairs[[length(pairs) + 1]] <- c(mark_label, numbers[[1]](mark))
  pairs
}

# mean = TRUE alone names the two centres, as it always has; a summary names every mark it draws.
spread_summary_legend <- function(summary, mean, drawn_marks) {
  if (is.null(summary) && !mean) return(list())
  summary_legend(if (is.null(summary)) c("median", "mean") else drawn_marks, "dot", hl_settings()$neutral$ink)
}

# The marks drawn: the default (median dot, IQR band, range line) or `summary`, with the mean when `mean`.
spread_summary <- function(summary, mean) {
  names <- if (is.null(summary)) spread_default_summary else check_summary(summary, "spread")
  if (mean && !"mean" %in% names) c(names, "mean") else names
}

# A row's marks: the range of the values drawn, the quartiles and mean held within it, and the interval bar (an SD or
# CI may reach past the values drawn; the axis widens for it).
spread_summary_row <- function(values, shown, names, discrete) {
  found <- summary_values(values, discrete)
  low <- min(shown)
  high <- max(shown)
  held <- function(value) min(max(value, low), high)
  bar <- intersect(names, summary_bars)
  ends <- if (identical(bar, "iqr")) {
    list(low = held(found$q1), high = held(found$q3), slim = FALSE)
  } else if (length(bar) && is.finite(found$sd)) {
    found_ends <- interval_of(found, bar)
    list(low = found_ends[1], high = found_ends[2], slim = TRUE)
  }
  list(low = low, high = high, range = "range" %in% names, bar = ends, median = held(found$median),
       show_median = "median" %in% names, mean = if ("mean" %in% names) held(found$mean))
}

spread_axis <- function(lows, highs, percent, zero) {
  low <- min(c(lows, if (zero) 0))
  high <- max(c(highs, if (zero) 0))
  breaks <- nice_breaks(low, high)
  limits <- axis_limits(low, high, breaks)
  shown <- snap_noise(breaks * if (percent) 100 else 1)
  labels <- vapply(shown, hl_format_number, character(1), digits = forest_decimals(shown))
  if (percent) labels[length(labels)] <- paste0(labels[length(labels)], locale_symbols(NULL)$percent_space, "%")
  list(breaks = breaks, labels = labels, low = limits[1], high = limits[2])
}

# The statistics to show, each once, and decimals as a whole number.
spread_check_options <- function(stats, digits) {
  unknown <- setdiff(stats, spread_stats)
  if (length(unknown)) {
    stop(sprintf("hairline: spread: unknown statistic '%s'; use any of %s", unknown[1],
                 paste(spread_stats, collapse = ", ")), call. = FALSE)
  }
  repeated <- unique(stats[duplicated(stats)])
  if (length(repeated)) {
    stop(sprintf("hairline: spread: stats names '%s' twice; name each statistic once", repeated[1]), call. = FALSE)
  }
  whole <- is.numeric(digits) && length(digits) == 1 && is.finite(digits) && digits >= 0 && digits == round(digits)
  if (!is.null(digits) && !whole) {
    stop(sprintf("hairline: spread: digits must be a whole number of 0 or more; got %s",
                 paste(format(digits), collapse = ", ")), call. = FALSE)
  }
}

# Reference values for groups that are drawn, as finite numbers: a mistyped group would lose its tick.
spread_check_marks <- function(marks, names) {
  if (length(marks) && is.null(names(marks))) {
    stop("hairline: spread: marks need group names, such as c(\"Unit A\" = 20)", call. = FALSE)
  }
  for (name in names(marks)) {
    if (!name %in% names) {
      stop(sprintf("hairline: spread: marks names '%s', which is not a group drawn; groups: %s", name,
                   paste(names, collapse = ", ")), call. = FALSE)
    }
    value <- marks[[name]]
    if (!is.numeric(value) || length(value) != 1 || !is.finite(value)) {
      stop(sprintf("hairline: spread: the mark for '%s' is %s; marks are finite numbers", name,
                   paste(format(value), collapse = ", ")), call. = FALSE)
    }
  }
}

# A median between two levels that each hold a large share matches neither (doses of 25 and 50 mg, median 35): say
# so, as a report would need a footnote for it.
warn_median_gaps <- function(groups, numbers, chart = "spread") {
  rules <- hl_tokens()$spread
  for (name in names(groups)) {
    gap <- median_gap(groups[[name]], rules$discrete_share, rules$discrete_min_n)
    if (is.null(gap)) next
    label <- if (nzchar(name)) sprintf(" of '%s'", name) else ""
    warning(sprintf(paste("hairline: %s: the median%s, %s, lies between %s and %s, which each hold more than %s of",
                          "the values, and matches neither; show stats = c(\"levels\", ...) or use discrete = TRUE"),
                    chart, label, numbers[[2]](stats::median(groups[[name]])), numbers[[1]](gap[1]),
                    numbers[[1]](gap[2]), hl_format_percent(rules$discrete_share, 0)), call. = FALSE)
  }
}

# Values per group (a named list), groups without a value left out.
group_samples <- function(data, group, value, order, chart) {
  names <- chart_groups(data, group, order, chart)
  samples <- lapply(names, function(name) {
    values <- as.numeric(data[[value]][!is.na(data[[group]]) & as.character(data[[group]]) == name])
    values[!is.na(values)]
  })
  samples <- stats::setNames(samples, names)
  samples[lengths(samples) > 0]
}

# The values drawn per group within the clip limits; a group left without one is refused.
clipped_samples <- function(samples, limits, chart) {
  drawn <- lapply(samples, within_limits, limits = limits)
  empty <- names(drawn)[lengths(drawn) == 0]
  if (length(empty)) {
    stop(sprintf("hairline: %s: clip hides every value of '%s'; widen the limits", chart, empty[1]), call. = FALSE)
  }
  drawn
}

# Rows by section (in the order sections first appear), then by median, highest first, when sorted.
arranged_rows <- function(rows, sort) {
  sections <- vapply(rows, function(row) row$section %||% "", character(1))
  rank <- match(sections, unique(sections))
  medians <- vapply(rows, `[[`, numeric(1), "median")
  rows[if (identical(sort, "median")) order(rank, -medians) else order(rank)]
}

spread_spec <- function(data, group, value, order = NULL, marks = NULL, mark_label = NULL,
                        stats = c("median", "iqr", "mean"), percent = FALSE, digits = NULL, zero = FALSE,
                        axis_title = NULL, colors = NULL, show_n = FALSE, min_n = NULL, clip = NULL,
                        clip_stats = FALSE, color_by = NULL, dimension = NULL, discrete = FALSE, section = NULL,
                        panel_letters = FALSE, mean = FALSE, sort = NULL, reference = NULL, highlight = NULL,
                        summary = NULL, compare = NULL, group_names = NULL) {
  check_columns(data, c(group, value, color_by, section))
  if (!is.null(sort) && !identical(sort, "median")) {
    stop(sprintf("hairline: spread: sort '%s' must be 'median' or NULL", sort), call. = FALSE)
  }
  spread_check_options(stats, digits)
  if (show_n && !"n" %in% stats) stats <- c(stats, "n")
  check_present(data, value, "spread")
  check_numeric(data, value, "spread")
  dropped <- drop_small(group_samples(data, group, value, order, "spread"), min_n, "spread")
  samples <- dropped$groups
  every <- unlist(samples, use.names = FALSE)
  limits <- clip_limits(every, clip, "spread")
  drawn <- clipped_samples(samples, limits, "spread")
  counted <- if (clip_stats) drawn else samples
  numbers <- measure_numbers(every, percent, digits, discrete)
  drawn_marks <- spread_summary(summary, mean)
  if (!discrete) warn_median_gaps(counted, numbers)
  names <- names(samples)
  spread_check_marks(marks, names)
  coloured <- series_colours(names, data, group, color_by, colors, dimension, "spread", highlight,
                             named = TRUE)
  lines <- option_references(reference, "spread")
  sections <- if (!is.null(section)) coarse_groups(data, group, section, "spread")
  rows <- lapply(names, function(name) {
    values <- counted[[name]]
    mark <- if (name %in% names(marks)) as.numeric(marks[[name]]) else NULL
    c(spread_summary_row(values, drawn[[name]], drawn_marks, discrete),
      list(name = name, color = coloured$palette[[name]], mark = mark,
           section = if (!is.null(section)) unname(sections[[name]]),
           pairs = spread_pairs(values, stats, numbers, mark, mark_label, discrete)))
  })
  rows <- arranged_rows(rows, sort)
  compared <- section_comparisons(rows, counted, compare, drawn_marks, numbers, "spread", group_names)
  rows <- compared$rows
  bar_ends <- unlist(lapply(rows, function(row) if (!is.null(row$bar)) c(row$bar$low, row$bar$high)))
  marked <- c(unlist(lapply(rows, `[[`, "mark")), vapply(lines, `[[`, numeric(1), "value"), bar_ends)
  notes <- c(dropped$note, if (!is.null(clip)) clip_caption(every, limits, clip_stats),
             if (discrete) word("levels_note"), compared$note)
  list(rows = rows, axis = spread_axis(c(vapply(rows, `[[`, numeric(1), "low"), marked),
                                       c(vapply(rows, `[[`, numeric(1), "high"), marked), percent, zero),
       axis_title = axis_title, notes = notes, letters = isTRUE(panel_letters),
       legend = c(if (!is.null(color_by)) coarse_legend(coloured), spread_summary_legend(summary, mean, drawn_marks)),
       references = lines)
}

faceted_spread_spec <- function(data, group, value, facet, order, options) {
  if (!is.null(options$section)) {
    stop("hairline: spread: facet and section both draw blocks of rows; give one of them", call. = FALSE)
  }
  keyed <- facet_rows(data, group, facet, order, "spread")
  names <- unique(unname(keyed$groups))
  coloured <- series_colours(names, data, group, options$color_by, options$colors, options$dimension, "spread",
                             options$highlight, named = TRUE)
  coarse_shown <- !is.null(options$color_by)
  marks <- options$marks
  keyed_marks <- if (length(marks)) {
    found <- keyed$keys[keyed$groups %in% names(marks)]
    stats::setNames(unname(marks[keyed$groups[found]]), found)
  }
  options[c("color_by", "dimension", "highlight")] <- list(NULL)
  options$colors <- stats::setNames(unname(coloured$palette[keyed$groups]), keyed$keys)
  options$marks <- if (length(keyed_marks)) keyed_marks else NULL
  options$section <- facet_block
  options$group_names <- keyed$groups
  spec <- do.call(spread_spec, c(list(keyed$data, facet_key, value, order = keyed$keys), options))
  for (index in seq_along(spec$rows)) spec$rows[[index]]$name <- unname(keyed$groups[spec$rows[[index]]$name])
  plain <- Filter(function(entry) !identical(entry$kind, "square"), spec$legend)
  spec$legend <- c(if (coarse_shown) coarse_legend(coloured), plain)
  spec
}

#' Spread rows: distributions per group on one axis
#'
#' Per group, first on top: the range as a thin line, the interquartile range
#' as a band in the group's colour, the median as a dot, an optional reference
#' tick, and the key numbers right-aligned. On a figure too narrow for the
#' numbers beside the plot, they sit on a line under each row.
#'
#' @param data A data frame.
#' @param group,value Grouping column and numeric column.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Group order, top to bottom.
#' @param marks Named reference values per group, e.g. `c("Unit A" = 20)` (a capacity, a target).
#' @param mark_label Name of the reference in the numbers column, e.g. `"beds"`.
#' @param stats Numbers to show: any of `"median"`, `"iqr"`, `"mean"`, `"n"`, `"range"`, `"sd"`, `"ci"` (the
#'   mean's 95% confidence interval), `"levels"` (the most frequent values with their shares). A median that
#'   falls between two large levels is warned about.
#' @param percent Values are shares (0-1), shown as percentages.
#' @param digits Decimals; default by magnitude (none for whole numbers).
#' @param zero Include zero on the axis.
#' @param axis_title Title under the axis numbers, e.g. the unit.
#' @param colors Named colours for this chart only.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param show_n Add each group's n to the numbers column.
#' @param min_n Leave out groups with fewer values; the caption names them.
#' @param clip Hide implausible values: a quantile of every value (`0.99`: above the 99th percentile) or
#'   `c(low, high)` (`NA` for no limit on that side); the caption says how many and where.
#' @param clip_stats Compute the statistics from the values drawn; by default they use every value.
#' @param color_by Colour the rows by a coarser column; the legend lists its values.
#' @param dimension What the groups are, so their colours keep off the slots another dimension holds (see
#'   [hl_scope()]).
#' @param discrete Keep quantiles on the data's own levels (type 1), for whole people or doses on round levels.
#' @param section Column whose values draw the rows in blocks, each under its name, on one shared axis.
#' @param panel_letters Letter the sections a, b, c.
#' @param mean Mark each row's mean as an open diamond; the legend row names median and mean.
#' @param summary The marks per row: any of `"median"` (a dot), `"mean"` (an open diamond), `"iqr"` (the band),
#'   `"range"` (a thin line), `"sd"` and `"ci"` (the mean's SD or 95% CI as a slim bar); one bar at most. The
#'   default is `c("median", "iqr", "range")`; a summary you give is named in the legend.
#' @param compare Write each row's difference against one group (`compare = "Unit A"`) or the row above
#'   (`"adjacent"`), with its 95% CI and p, beside the other numbers (within each block); the caption names the
#'   test, which follows the centre: the Hodges-Lehmann shift and Wilcoxon rank-sum test with the median, the
#'   difference in means and Welch's t-test with the mean alone.
#' @param numbers Where the numbers go: beside the plot while it keeps its least width, else under each row
#'   (`"auto"`), always beside it (`"right"`), or always under each row (`"below"`).
#' @param sort `"median"` orders the rows of a section by median, highest first; `NULL` keeps their order.
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' beds <- data.frame(unit = rep(c("Unit A", "Unit B", "Unit C"), each = 50),
#'                    occupied = c(stats::rpois(50, 10), stats::rpois(50, 7), stats::rpois(50, 12)))
#' hl_spread(beds, "unit", "occupied", marks = c("Unit A" = 12, "Unit B" = 8, "Unit C" = 14),
#'           mark_label = "Beds",
#'           zero = TRUE, axis_title = "Occupied beds")
#' @export
hl_spread <- function(data, group, value, title = NULL, subtitle = NULL, caption = NULL, order = NULL, marks = NULL,
                      mark_label = NULL, stats = c("median", "iqr", "mean"), percent = FALSE, digits = NULL,
                      zero = FALSE, axis_title = NULL, colors = NULL, show_n = FALSE, min_n = NULL, clip = NULL,
                      clip_stats = FALSE, color_by = NULL, dimension = NULL, discrete = FALSE, section = NULL,
                      panel_letters = FALSE, mean = FALSE, sort = NULL, x_title = NULL, reference = NULL,
                      highlight = NULL, key_title = NULL, facet = NULL, summary = NULL, compare = NULL,
                      numbers = "auto", reference_legend = FALSE) {
  options <- list(summary = summary, compare = compare, marks = marks, mark_label = mark_label, stats = stats,
                  percent = percent, digits = digits,
                  zero = zero, axis_title = axis_title %||% x_title, colors = colors, show_n = show_n, min_n = min_n,
                  clip = clip, clip_stats = clip_stats, color_by = color_by, dimension = dimension,
                  discrete = discrete, section = section, panel_letters = panel_letters, mean = mean, sort = sort,
                  reference = legend_references(reference, reference_legend, "spread")$reference,
                  highlight = highlight)
  spec <- if (is.null(facet)) do.call(spread_spec, c(list(data, group, value, order = order), options)) else
    faceted_spread_spec(data, group, value, facet, order, options)
  spec$numbers <- check_numbers(numbers, "spread")
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(value), "by", gsub("_", " ", group)), subtitle = subtitle,
                  caption = with_caption(caption, spec$notes), x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  if (length(spec$legend)) plot <- plot + hl_legend(spec$legend)
  plot@meta$hairline_drawing <- function(box, measure, style) spread_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_key_title <- key_title
  plot@meta$hairline_reference_legend <- legend_references(reference, reference_legend, "spread")$labels
  plot
}
