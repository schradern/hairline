# Ridgeline plot, mirroring the Python ridgeline(): one density ridge per group on a shared x-axis, the first
# group on top, overlapping the row above, medians marked.

# Each group's values among the rows `here` (all rows without a facet); a group absent there has none. As Python's
# panel_groups().
ridgeline_groups <- function(data, group, value, names, here) {
  stats::setNames(lapply(names, function(name) {
    as.numeric(stats::na.omit(data[[value]][here & as.character(data[[group]]) == name]))
  }), names)
}

# The share of the plot height a reference label hangs into from the top (its gap, cap height and gap at the caption
# size), on the least plot height, so the top ridge stays clear of it; 0 without labels. As Python's label_room().
ridgeline_label_room <- function(reference) {
  labelled <- any(vapply(option_references(reference, "ridgeline"), function(line) !is.null(line$label), logical(1)))
  if (!labelled) return(0)
  tokens <- hl_tokens()
  label <- tokens$type$roles$caption$factor * (2 * tokens$reference$label_gap + font_metrics()$cap_height)
  label / tokens$spacing$min_plot_height
}

# Every ridge's measures as key-number pairs and, with `compare`, its delta and p against the reference or the ridge
# above, within its panel; the values by row key; and the caption note naming the test. As Python's ridge_rows().
ridge_rows <- function(panels, measures, every, percent, compare, marks) {
  numbers <- measure_numbers(every, percent, NULL)
  rows <- list()
  values <- list()
  for (index in seq_along(panels)) {
    groups <- panels[[index]]
    for (position in seq_along(groups)) {
      key <- paste0(index, "\u001f", names(groups)[position])
      values[[key]] <- groups[[position]]
      rows[[length(rows) + 1]] <- list(name = key, section = index, count = length(groups), position = position,
                                       pairs = if (length(groups[[position]])) {
                                         stat_pairs(groups[[position]], measures, numbers)
                                       } else {
                                         list()
                                       })
    }
  }
  group_names <- stats::setNames(sub("^[0-9]+\u001f", "", names(values)), names(values))
  compared <- section_comparisons(rows, values, compare, marks, numbers, "ridgeline", group_names)
  list(rows = compared$rows, values = values, note = compared$note)
}

# Each panel's numbers column: every ridge's measures and, with `compare`, its delta and p against the reference or
# the ridge above, at its baseline (a group without values in a panel has none); and the caption note naming the
# test. As Python's ridge_numbers().
ridge_numbers <- function(panels, stats, every, percent, compare, marks) {
  compared <- ridge_rows(panels, stats, every, percent, compare, marks)
  values <- compared$values
  columns <- lapply(seq_along(panels), function(index) {
    unlist(lapply(Filter(function(row) row$section == index && length(values[[row$name]]), compared$rows),
                  function(row) {
                    lapply(row$pairs, function(pair) {
                      list(position = row$count - row$position, label = pair[1], value = pair[2])
                    })
                  }), recursive = FALSE)
  })
  list(columns = columns, note = compared$note)
}

# Each panel's ridge tooltips by group: the marks it draws and the numbers beside it, its n, and its delta and p with
# `compare`, in the numbers column's digits; a group without values in a panel has none. As Python's ridge_tips().
ridge_tips <- function(panels, stats, every, percent, compare, marks) {
  compared <- ridge_rows(panels, tip_measures(marks, stats), every, percent, compare, marks)
  lapply(seq_along(panels), function(index) {
    rows <- Filter(function(row) row$section == index && length(compared$values[[row$name]]), compared$rows)
    names <- sub("^[0-9]+\u001f", "", vapply(rows, `[[`, character(1), "name"))
    stats::setNames(lapply(seq_along(rows), function(position) pairs_tip(names[position], rows[[position]]$pairs)),
                    names)
  })
}

ridgeline_why <- "A ridge shows its own spread; hl_raincloud() and hl_spread() draw intervals"

#' Ridgeline plot
#'
#' One density ridge per group on a shared x-axis, the first group on top,
#' each overlapping the row above; all ridges share one height scale, and a
#' short line marks each median.
#'
#' @param data A data frame.
#' @param group,value Columns: the grouping and the measurement; or a formula `value ~ group` as `group`.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param order Group order, top to bottom.
#' @param medians Mark the medians.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param show_n Write each group's n after its name, in the locale; with `facet`, each panel's n in its header.
#' @param min_n,clip,clip_stats,color_by,dimension As in [hl_spread()]: groups too small and values clipped off are
#'   named in the caption.
#' @param columns Panels per row with `facet` (two by default).
#' @param summary The marks on each ridge: `"median"` (a line up to the ridge) and `"mean"` (an open diamond on its
#'   outline); by default the median, or nothing with `medians = FALSE`. A summary you give is named in the
#'   legend. A ridge shows its own spread, so intervals belong to [hl_raincloud()] or [hl_spread()].
#' @param stats Measures beside each ridge, in a column right of the plot: any of `"median"`, `"mean"`, `"iqr"`,
#'   `"range"`, `"sd"`, `"ci"`, `"n"`.
#' @param compare Add each ridge's difference against one group or the ridge above (`"adjacent"`), with its 95% CI
#'   and p, to that column (within each panel); the caption names the test, which follows the centre as in
#'   [hl_spread()].
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' set.seed(1)
#' diagnoses <- c("Sepsis", "Trauma", "Cardiac", "Respiratory", "Neuro")
#' ages <- data.frame(diagnosis = rep(diagnoses, each = 40),
#'                    age = round(stats::rnorm(200, rep(c(68, 45, 70, 62, 55), each = 40), 10)))
#' hl_ridgeline(ages, "diagnosis", "age")
#' @export
hl_ridgeline <- function(data, group, value = NULL, title = NULL, subtitle = NULL, caption = NULL, order = NULL,
                         medians = TRUE, colors = NULL, show_n = FALSE, min_n = NULL, clip = NULL, clip_stats = FALSE,
                         color_by = NULL, dimension = NULL, sort = NULL, percent = FALSE, x_title = NULL,
                         reference = NULL, highlight = NULL, key_title = NULL, facet = NULL, columns = NULL,
                         summary = NULL, stats = character(), compare = NULL, reference_legend = FALSE) {
  if (inherits(group, "formula")) {
    sides <- formula_sides(group)
    value <- deparse(sides$left)
    group <- sides$right[1]
  }
  check_columns(data, c(group, value, color_by, facet))
  check_present(data, value, "ridgeline")
  check_numeric(data, value, "ridgeline")
  marks <- if (is.null(summary)) {
    if (medians) "median" else character()
  } else {
    check_summary(summary, "ridgeline", summary_centres, ridgeline_why)
  }
  stats <- as_names(stats, "ridgeline", "stats", stat_names)
  rules <- hl_tokens()$ridgeline
  names <- chart_groups(data, group, order, "ridgeline")
  groups <- ridgeline_groups(data, group, value, names, rep(TRUE, nrow(data)))
  dropped <- drop_small(groups, min_n, "ridgeline")
  groups <- dropped$groups[sorted_names(names(dropped$groups), function(name) dropped$groups[[name]], sort,
                                        "ridgeline")]
  names <- names(groups)
  every <- unlist(groups, use.names = FALSE)
  limits <- clip_limits(every, clip, "ridgeline")
  panels <- if (is.null(facet)) "" else chart_groups(data, facet, NULL, "ridgeline")
  counted <- lapply(panels, function(panel) {
    if (is.null(facet)) groups else ridgeline_groups(data, group, value, names, as.character(data[[facet]]) == panel)
  })
  drawn <- lapply(counted, function(here) lapply(here, within_limits, limits = limits))
  curves <- lapply(drawn, function(here) lapply(here, density_curve))
  heights <- unlist(lapply(curves, function(here) lapply(here, function(curve) max(c(0, curve$height)))))
  peak <- max(c(0, heights))
  scale <- (1 + rules$overlap) / if (peak > 0) peak else 1
  palette <- series_colours(names, data, group, color_by, colors, dimension, "ridgeline", highlight,
                            named = TRUE)
  plot <- ggplot2::ggplot()
  numbers <- ridge_numbers(if (clip_stats) drawn else counted, stats, every, percent, compare, marks)
  tips <- ridge_tips(if (clip_stats) drawn else counted, stats, every, percent, compare, marks)
  targets <- list()
  # Labels named in the legend row take no room above the ridges.
  drawn_references <- legend_references(reference, reference_legend, "ridgeline")$reference
  top <- (length(names) + rules$overlap + rules$headroom) / (1 - ridgeline_label_room(drawn_references))
  lifts <- numeric()
  for (index in seq_along(panels)) {
    statistics <- if (clip_stats) drawn[[index]] else counted[[index]]
    built <- ridgeline_panel_layers(drawn[[index]], curves[[index]], statistics, scale, marks, palette$palette,
                                    ridge_mean_floor(top))
    bottom <- built$ridges[[names[length(names)]]]$marks
    lifts <- c(lifts, unlist(lapply(Filter(function(mark) !is.null(mark$diamond), bottom), function(mark) {
      mark$diamond[2]
    })))
    layers <- built$layers
    for (name in names(built$ridges)) {
      ridge <- built$ridges[[name]]
      tip <- if (!is.null(tips[[index]][[name]])) list(list(at = ridge$at, text = tips[[index]][[name]])) else list()
      targets[[length(targets) + 1]] <- chart_target(index, name, palette$palette[[name]], ridge$marks, tip)
    }
    plot <- plot + if (is.null(facet)) layers else in_facet(layers, panels[index], panels)
    if (!is.null(facet)) {
      total <- sum(lengths(statistics))
      plot <- plot + hl_panel_header(panel = panels[index], name = panels[index],
                                     stats = if (show_n) c(n = hl_format_number(total, 0)) else NULL)
    }
  }
  labels <- if (show_n && is.null(facet)) labels_with_n(names, lengths(groups)) else names
  notes <- c(dropped$note, if (!is.null(clip)) clip_caption(every, limits, clip_stats), numbers$note)
  plot <- plot + ggplot2::scale_y_continuous(breaks = rev(seq_along(names) - 1), labels = labels, expand = c(0, 0),
                                             limits = c(0, top)) +
    ggplot2::labs(title = title %||% paste(humanise(value), "by", gsub("_", " ", group)), subtitle = subtitle,
                  caption = with_caption(caption, notes), x = humanise(value), y = NULL) + theme_hairline()
  if (!is.null(facet)) {
    plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.facet), ncol = columns %||% min(length(panels), 2))
  }
  legend <- c(if (!is.null(color_by)) coarse_legend(palette),
              if (!is.null(summary)) summary_legend(marks, "tick", hl_settings()$neutral$ink))
  if (length(legend)) plot <- plot + hl_legend(legend)
  if (any(lengths(numbers$columns) > 0)) plot@meta$hairline_side_numbers <- numbers$columns
  # A mean diamond on a flat bottom ridge would reach below the panel on a short plot: the plot grows instead.
  panel_columns <- if (is.null(facet)) 1 else columns %||% min(length(panels), 2)
  plot@meta$hairline_min_plot <- ridge_mean_plot_height(lifts, top, ceiling(length(panels) / panel_columns))
  plot@meta$hairline_targets <- targets
  if (percent) plot <- plot + scale_x_hairline(percent = TRUE)
  chart_options(plot, "ridgeline", names, x_title = x_title, reference = reference,
                reference_legend = reference_legend, reference_axis = "x",
                key_title = key_title)
}
