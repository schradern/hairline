# Bar chart, mirroring the Python bars(): counts or sums per category, side by side or stacked, vertical or
# horizontal, values at the bar ends.

bar_table <- function(data, category, value, by, order, sort, groups = NULL) {
  if (!sort %in% c("value", "given")) {
    stop(sprintf("hairline: bars: sort '%s' must be 'value' or 'given'", sort), call. = FALSE)
  }
  check_labels(data, c(category, by), "bars")
  check_present(data, value, "bars")
  check_numeric(data, value, "bars")
  names <- ordered_names(data[[category]], order, "bars", category)
  groups <- groups %||% if (is.null(by)) "" else group_names(data[[by]])
  keys <- if (is.null(by)) as.character(data[[category]]) else
    combination_key(data[[category]], data[[by]])
  first <- !duplicated(keys)
  table <- data[first, c(category, by), drop = FALSE]
  table[[category]] <- as.character(table[[category]])
  # A cell whose values are all missing stays missing (no bar, label or tooltip); for sorting and percent totals it
  # counts as zero.
  table$.value <- as.numeric(tapply(data[[value]], factor(keys, levels = unique(keys)), function(values) {
    if (all(is.na(values))) NA_real_ else sum(values, na.rm = TRUE)
  }))
  # Categories left out of `order` are not drawn.
  table <- table[table[[category]] %in% names, , drop = FALSE]
  if (identical(sort, "value") && is.null(order)) {
    totals <- tapply(table$.value, table[[category]], sum, na.rm = TRUE)
    names <- names[order(-totals[names], seq_along(names))]
  }
  list(table = table, names = names, groups = groups)
}

# The `top` largest categories (by their totals) keep their order; the rest sum into one bar named `other`, drawn last.
# A category already named `other` joins the rest.
fold_top <- function(parts, top, other, category, by) {
  if (is.null(top) || length(parts$names) <= top) return(parts)
  table <- parts$table
  totals <- tapply(table$.value, factor(table[[category]], levels = parts$names), sum, na.rm = TRUE)
  totals[is.na(totals)] <- 0
  ranked <- parts$names[order(-totals[parts$names], seq_along(parts$names))][seq_len(top)]
  kept <- parts$names[parts$names %in% ranked & parts$names != other]
  table[[category]][!table[[category]] %in% kept] <- other
  keys <- if (is.null(by)) table[[category]] else combination_key(table[[category]], table[[by]])
  folded <- table[!duplicated(keys), , drop = FALSE]
  folded$.value <- as.numeric(tapply(table$.value, factor(keys, levels = unique(keys)), function(values) {
    if (all(is.na(values))) NA_real_ else sum(values, na.rm = TRUE)
  }))
  list(table = folded, names = c(kept, other), groups = parts$groups)
}

check_top <- function(top, scales) {
  whole <- is.numeric(top) && length(top) == 1 && is.finite(top) && top >= 1 && top == round(top)
  if (!is.null(top) && !whole) {
    stop(sprintf("hairline: bars: top must be a whole number of 1 or more; got %s",
                 paste(format(top), collapse = ", ")), call. = FALSE)
  }
  if (!scales %in% c("free", "shared")) {
    stop(sprintf("hairline: bars: scales '%s' must be one of free, shared", scales), call. = FALSE)
  }
}

# Each category's total across the groups: the n a share chart would otherwise lose.
category_n <- function(parts, category) {
  totals <- tapply(parts$table$.value, factor(parts$table[[category]], levels = parts$names), sum, na.rm = TRUE)
  totals[is.na(totals)] <- 0
  stats::setNames(as.numeric(totals), parts$names)
}

# Per facet: its table (the smallest categories folded into `other`), category order, labels and total.
facet_panels <- function(data, category, value, by, facet, order, sort, groups, options) {
  facets <- if (is.null(facet)) "" else group_names(data[[facet]])
  lapply(facets, function(name) {
    rows <- if (is.null(facet)) data else data[as.character(data[[facet]]) == name, , drop = FALSE]
    parts <- fold_top(bar_table(rows, category, value, by, order, sort, groups), options$top, options$other, category,
                      by)
    # An answer outside the ranking (an exclusive "none") goes last.
    if (identical(sort, "value")) parts$names <- c(setdiff(parts$names, options$context),
                                                   intersect(parts$names, options$context))
    counts <- category_n(parts, category)
    c(parts, list(facet = name, n = counts, total = sum(parts$table$.value, na.rm = TRUE),
                  labels = if (isTRUE(options$show_n)) labels_with_n(parts$names, counts) else parts$names))
  })
}

bars_horizontal <- function(names) {
  rules <- hl_tokens()$bars
  length(names) > rules$horizontal_count || max(nchar(names)) > rules$horizontal_length
}

# Upright bars need every category name, and every value over its bar, to fit the room a category gets across the
# plot (the figure's width less its margins and the y labels, about as wide as the widest value), with
# `bars.label_space` x the base size between neighbours; otherwise the bars lie down.
fits_upright <- function(names, values, bars_per_slot, width_pt, settings) {
  tokens <- hl_tokens()
  base <- settings$base_size
  measure <- measure_for(settings)
  widest <- max(c(0, vapply(values, measure, numeric(1), role = "label")))
  plot <- width_pt - 2 * tokens$spacing$margin * base - widest - tokens$spacing$y_labels_plot * base
  slot <- plot / (length(names) - 1 + 2 * tokens$bars$category_pad)
  space <- tokens$bars$label_space * base
  max(vapply(names, measure, numeric(1), role = "label")) <= slot - space && widest <= slot / bars_per_slot - space
}

# The value texts upright bars would carry over their ends: every bar's, or each stack's total.
upright_values <- function(frame, stacked, labels, percent) {
  if (!labels || (stacked && percent)) return(character())
  if (!stacked) return(frame$label)
  totals <- tapply(frame$value, frame$category, sum)
  vapply(totals[!is.na(totals)], format_compact, character(1), digits = attr(frame, "digits"),
         unit = attr(frame, "unit"))
}

# Many or long labels (as drawn, with their n) lie down, and so do labels too wide for upright bars at the width of
# `size` (the host's column, else the preset's width), shared by the panel columns; one decision for every panel.
bars_lie_down <- function(panels, category, by, stacked, labels, percent, size, columns = 1, divide = percent) {
  if (any(vapply(panels, function(parts) bars_horizontal(parts$labels), logical(1)))) return(TRUE)
  figure <- default_figure(size)
  !all(vapply(panels, function(parts) {
    values <- upright_values(bar_frame(parts, category, by, FALSE, percent, stacked, divide), stacked, labels, percent)
    fits_upright(parts$labels, values, if (stacked) 1 else length(parts$groups), figure$width_pt / columns,
                 figure$settings)
  }, logical(1)))
}

# Decimals and unit of the values on the bars: the data's own decimals, or, from 10^9 on, one short-scale unit for
# the chart (1.2 tn, 0.8 tn) with `numbers.compact_digits` decimals.
bar_numbers <- function(table, category, stacked) {
  values <- c(table$.value, if (stacked) tapply(table$.value, table[[category]], sum))
  unit <- number_unit(values)
  if (is.null(unit)) list(digits = auto_digits(table$.value), unit = NULL) else
    list(digits = hl_tokens()$numbers$compact_digits, unit = unit)
}

bar_frame <- function(parts, category, by, horizontal, percent, stacked = FALSE, divide = percent) {
  table <- parts$table
  numbers <- bar_numbers(table, category, stacked)
  digits <- numbers$digits
  if (divide) {
    negative <- which(table$.value < 0)
    if (length(negative)) {
      stop(sprintf("hairline: bars: percent needs values of zero or more; '%s' has %s", table[[category]][negative[1]],
                   format(table$.value[negative[1]])), call. = FALSE)
    }
    totals <- stats::ave(table$.value, table[[category]], FUN = function(values) sum(values, na.rm = TRUE))
    empty <- table[[category]][!(totals > 0)]
    if (length(empty)) {
      stop(sprintf(paste("hairline: bars: percent needs a total above zero in every category; '%s' totals %s,",
                         "so its shares are undefined"), empty[1], format(totals[!(totals > 0)][1])), call. = FALSE)
    }
    table$.value <- table$.value / totals
  }
  levels <- if (horizontal) rev(parts$names) else parts$names
  # A bar's value: whole percentages, or the data's own decimals (0.12 stays 0.12, counts stay whole), in the chart's
  # unit when its numbers are that large (see bar_numbers()).
  frame <- data.frame(category = factor(table[[category]], levels = levels),
                      group = factor(if (is.null(by)) "" else as.character(table[[by]]), levels = parts$groups),
                      value = table$.value,
                      label = if (percent) vapply(table$.value, hl_format_percent, character(1), digits = 0) else
                        vapply(table$.value, format_compact, character(1), digits = digits, unit = numbers$unit))
  frame$.name <- as.character(table[[category]])
  attr(frame, "digits") <- digits
  attr(frame, "unit") <- numbers$unit
  frame[!is.na(frame$value), , drop = FALSE]
}

bar_value_mapping <- function(horizontal) {
  if (horizontal) {
    ggplot2::aes(.data$value, .data$category, label = .data$label, group = .data$group)
  } else {
    ggplot2::aes(.data$category, .data$value, label = .data$label, group = .data$group)
  }
}

bar_text <- function(mapping, frame, position, colour, settings, ...) {
  ggplot2::geom_text(mapping, data = frame, position = position, colour = colour, family = settings$font,
                     size = role_size(settings, "label") / ggplot2::.pt, ...)
}

stacked_text_layers <- function(frame, colours, horizontal, percent) {
  rules <- hl_tokens()$bars
  settings <- hl_settings()
  largest <- if (percent) 1 else max(tapply(pmax(frame$value, 0), frame$category, sum), na.rm = TRUE)
  shown <- frame
  shown$label[shown$value < rules$segment_min * largest | shown$value <= 0] <- ""
  style <- list(neutral = settings$neutral)
  inks <- vapply(as.character(shown$group), function(name) contrast_text(colours[[name]], style), character(1))
  layers <- list(bar_text(bar_value_mapping(horizontal), shown, ggplot2::position_stack(vjust = 0.5, reverse = TRUE),
                          inks, settings))
  if (!percent) {
    ups <- tapply(pmax(frame$value, 0), frame$category, sum)
    downs <- tapply(pmin(frame$value, 0), frame$category, sum)
    present <- !is.na(ups)
    # The signed total at the end of the stack: past the positive segments, or the negative ones if none is positive.
    totals <- with_facet(data.frame(category = factor(names(ups)[present], levels = levels(frame$category)),
                                    value = ifelse(ups > 0, ups, downs)[present], group = "",
                                    label = vapply((ups + downs)[present], format_compact, character(1),
                                                   digits = attr(frame, "digits") %||% 0, unit = attr(frame, "unit"))),
                         frame)
    gap <- rules$label_gap
    layers[[2]] <- bar_text(bar_value_mapping(horizontal), totals, "identity", settings$neutral$muted, settings,
                            hjust = if (horizontal) -gap else 0.5, vjust = if (horizontal) 0.5 else -gap)
  }
  layers
}

# Groups side by side; horizontal bars run top-down in legend order.
bar_dodge <- function(horizontal) ggplot2::position_dodge(width = hl_tokens()$bars$width, reverse = horizontal)

# Room on the value axis for the labels at the bar ends.
# Shares of respondents end at 100 % (`cap`); a label past it may run into the margin.
bar_headroom <- function(frame, horizontal, percent, stacked, cap = Inf) {
  if (stacked && percent) return(list())
  largest <- if (stacked) max(tapply(pmax(frame$value, 0), frame$category, sum), na.rm = TRUE) else max(frame$value)
  reach <- with_facet(data.frame(category = factor(levels(frame$category)[1], levels = levels(frame$category)),
                                 value = min(largest * (1 + hl_tokens()$bars$label_headroom), cap)), frame)
  mapping <- if (horizontal) ggplot2::aes(.data$value, .data$category) else ggplot2::aes(.data$category, .data$value)
  list(ggplot2::geom_blank(mapping, data = reach, inherit.aes = FALSE))
}

# A layer's own rows carry the facet of the frame they were computed from.
with_facet <- function(rows, frame) {
  if (".facet" %in% names(frame)) rows$.facet <- rep(frame$.facet[1], nrow(rows))
  rows
}

# Space before the first and after the last category, as in Python; `labels` maps a category to the text drawn
# (with its n, or without the facet the category is keyed by).
bar_category_scale <- function(horizontal, labels = NULL) {
  expand <- ggplot2::expansion(add = hl_tokens()$bars$category_pad)
  shown <- if (is.null(labels)) ggplot2::waiver() else function(breaks) unname(labels[as.character(breaks)])
  if (horizontal) ggplot2::scale_y_discrete(expand = expand, labels = shown) else
    ggplot2::scale_x_discrete(expand = expand, labels = shown)
}

# The fill colours and their legend labels: each group's own name, or with `color_by` its coarser value.
bar_fill_scale <- function(colours, series) {
  shown <- length(unique(unname(colours))) > 1 || (is.null(series) && length(colours) > 1)
  labels <- if (is.null(series)) ggplot2::waiver() else unname(series[names(colours)])
  ggplot2::scale_fill_manual(values = colours, breaks = names(colours), labels = labels,
                             guide = if (shown) "legend" else "none")
}

bar_layers <- function(frames, colours, horizontal, stacked, labels, percent, series = NULL, partial = FALSE,
                       context = character(), cap = Inf) {
  rules <- hl_tokens()$bars
  settings <- hl_settings()
  frame <- if (length(frames) == 1) frames[[1]] else do.call(rbind, frames)
  position <- if (stacked) ggplot2::position_stack(reverse = TRUE) else bar_dodge(horizontal)
  mapping <- if (horizontal) ggplot2::aes(.data$value, .data$category, fill = .data$group) else
    ggplot2::aes(.data$category, .data$value, fill = .data$group)
  if (partial) mapping$alpha <- quote(.data$.alpha)
  edge <- if (stacked) list(colour = settings$neutral$surface, linewidth = pt_to_linewidth(rules$gap_pt / 2)) else
    list(colour = NA)
  receding <- frame$.name %in% context
  if (any(receding)) {
    mapping$alpha <- quote(.data$.alpha)
    frame$.alpha[receding] <- 0
  }
  layers <- list(do.call(ggplot2::geom_col, c(list(mapping, data = frame, position = position,
                                                   width = rules$width * 0.92,
                                                   orientation = if (horizontal) "y" else "x"), edge)),
                 bar_fill_scale(colours, series))
  if (any(receding)) layers[[length(layers) + 1]] <- ggplot2::scale_alpha_identity()
  if (any(receding)) layers <- c(layers, list(context_layer(frame[receding, , drop = FALSE], mapping, position,
                                                            horizontal, edge)))
  if (partial) layers[[length(layers) + 1]] <- ggplot2::scale_alpha_identity()
  if (!labels) return(layers)
  if (stacked) {
    texts <- lapply(frames, function(one) {
      c(stacked_text_layers(one, colours, horizontal, percent), bar_headroom(one, horizontal, percent, TRUE))
    })
    return(c(layers, unlist(texts, recursive = FALSE)))
  }
  gap <- rules$label_gap
  c(layers, unlist(lapply(frames, bar_headroom, horizontal = horizontal, percent = percent, stacked = FALSE,
                          cap = cap), recursive = FALSE),
    list(bar_text(bar_value_mapping(horizontal), frame, bar_dodge(horizontal),
                  settings$neutral$muted, settings, hjust = if (horizontal) -gap else 0.5,
                  vjust = if (horizontal) 0.5 else -gap)))
}

# "Count by unit", or "Count by unit and sex" when bars are split by a second column.
bars_title <- function(value, category, by) {
  split <- if (!is.null(by) && !identical(by, category)) paste(" and", gsub("_", " ", by)) else ""
  paste0(humanise(value), " by ", gsub("_", " ", category), split)
}

# One frame per panel. Facets key each category by its facet (each panel has its own categories and their n), so
# `labels` maps the keys back to the text drawn; incomplete periods get their lighter opacity.
bar_frames <- function(panels, category, by, horizontal, percent, stacked, facet, partial, divide = percent) {
  faceted <- !is.null(facet)
  labels <- character()
  opacity <- hl_tokens()$partial$opacity
  frames <- lapply(panels, function(parts) {
    frame <- bar_frame(parts, category, by, horizontal, percent, stacked, divide)
    keys <- if (faceted) paste0(parts$facet, "\037", parts$names) else parts$names
    labels[keys] <<- parts$labels
    levels <- if (horizontal) rev(keys) else keys
    frame$category <- factor(keys[match(frame$.name, parts$names)], levels = levels)
    if (faceted) frame$.facet <- factor(rep(parts$facet, nrow(frame)), levels = vapply(panels, `[[`, "", "facet"))
    frame$.alpha <- ifelse(frame$.name %in% names(partial), opacity, 1)
    frame
  })
  relabelled <- faceted || any(labels != names(labels))
  list(frames = frames, labels = if (relabelled) labels)
}

# Facets share the value axis when `scales` is shared; the category axis is each panel's own.
bar_facet_scales <- function(scales, horizontal) {
  if (scales == "shared") return(if (horizontal) "free_y" else "free_x")
  "free"
}

# Each facet's name and total in its panel header.
# Each facet's name and its total, or its n: the respondents of a multiple-choice panel, else its total count.
bar_facet_headers <- function(panels, header = "total", respondent_n = list()) {
  lapply(panels, function(parts) {
    stat <- if (header == "n") {
      stats::setNames(hl_format_number(respondent_n[[parts$facet]] %||% parts$total, 0), "n")
    } else {
      stats::setNames(hl_format_number(parts$total, auto_digits(parts$total)), word("total"))
    }
    hl_panel_header(panel = parts$facet, stats = stat)
  })
}

# The groups' colours (one per value of `color_by`, when given) and the legend label each stands for.
bar_colours <- function(data, by, groups, color_by, colors, dimension) {
  if (is.null(by)) return(list(colours = stats::setNames(lone_colour(), ""), series = NULL))
  if (is.null(color_by)) return(list(colours = colours_for(groups, colors, dimension), series = NULL))
  series <- coarse_groups(data, by, color_by, "bars")[groups]
  palette <- colours_for(unique(unname(series)), colors, dimension)
  list(colours = stats::setNames(unname(palette[series]), groups), series = stats::setNames(unname(series), groups))
}

#' Bar chart
#'
#' Bars per category; without `value` the rows are counted. Long or many
#' labels turn the bars horizontal; a single series is sorted by value unless
#' `order` or `sort = "given"` says otherwise. Values sit at the bar ends.
#'
#' @param data A data frame.
#' @param category Column with the categories.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param by Grouping column; groups side by side, or stacked with `stacked = TRUE`.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param stacked Stack the groups.
#' @param percent Show shares of each category instead of amounts.
#' @param horizontal Force horizontal (`TRUE`) or vertical (`FALSE`) bars. By default many or long labels lie
#'   down, and so do labels too wide for upright bars at the width of `size`.
#' @param sort `"value"` or `"given"`; default by value, except for groups side by side.
#' @param order Category order.
#' @param labels Print the values: at the bar ends, or inside stacked segments with the totals at the ends.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#'   A ramp name such as `"blues"` colours ordered groups light to dark, in the chart's order.
#' @param size Size preset the bars are laid out for, as in [hl_save()] (`NULL`: `"onehalf"`): its width decides
#'   between upright and lying bars, and [hl_save()] uses it unless given another size.
#' @param facet Column to draw one panel per value of, each with its own value axis (`scales = "free"`) or one
#'   shared axis (`scales = "shared"`), the facet's name and total in its panel header.
#' @param scales `"free"` or `"shared"` value axes across facets.
#' @param columns Panel columns for facets (default: up to 2).
#' @param top Keep the `top` largest categories per panel and fold the rest into one bar named `other`.
#' @param other Name of the folded bar (default: the locale's "Other").
#' @param partial Incomplete periods and what they hold, e.g. `c("2021" = "2 months")`: drawn lighter and named in
#'   the caption, in the locale.
#' @param show_n Write each category's n after its label (`TRUE`), or in a column right of the bars
#'   (`"column"`); colours and `order` keep keying on the bare name.
#' @param normalize Draw shares of each category's total (as `percent`) and keep the n in the labels.
#' @param color_by Colour the groups of `by` by a coarser column, whose values the legend lists.
#' @param dimension What the groups are, so their colours keep off the slots another dimension holds (see
#'   [hl_scope()]).
#' @param context Categories drawn in the context grey (an exclusive "none" answer), last when sorted by value.
#' @param header `"total"` or `"n"`: what each facet's panel header gives beside its name.
#' @param inside `"name"` writes each stacked segment's name and value inside it, in greys by position, so rows may
#'   hold different answers and no legend is needed.
#' @param respondents Column naming the respondent of each multiple-choice answer (one row per answer): each
#'   respondent counts once per answer, as a share of the panel's respondents; the caption says several answers
#'   were possible.
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' admissions <- data.frame(
#'   diagnosis = c("Sepsis", "Sepsis", "Trauma", "Cardiac", "Cardiac", "Cardiac"),
#'   sex = c("Female", "Male", "Male", "Female", "Male", "Male"))
#' hl_bars(admissions, "diagnosis")
#' hl_bars(admissions, "diagnosis", by = "sex", stacked = TRUE)
#' cases <- data.frame(year = rep(2021:2023, 2), group = rep(c("Large", "Small"), each = 3),
#'                     cases = c(120, 900, 950, 4, 30, 28))
#' hl_bars(cases, "year", "cases", facet = "group", sort = "given", partial = c("2021" = "2 months"))
#' @export
hl_bars <- function(data, category, value = NULL, by = NULL, title = NULL, subtitle = NULL, caption = NULL,
                    stacked = FALSE, percent = FALSE, horizontal = NULL, sort = NULL, order = NULL, labels = TRUE,
                    colors = NULL, size = NULL, facet = NULL, scales = "free", columns = NULL, top = NULL,
                    other = NULL, partial = NULL, show_n = FALSE, normalize = FALSE, color_by = NULL,
                    dimension = NULL, context = NULL, header = "total", inside = NULL, respondents = NULL,
                    min_n = NULL, x_title = NULL, y_title = NULL, reference = NULL, highlight = NULL,
                    key_title = NULL) {
  if (!is.null(size)) check_size_preset(size)
  kept <- without_small_categories(data, category, min_n, "bars")
  data <- kept$data
  respondent_n <- list()
  if (!is.null(respondents)) {
    check_respondents(value, by, percent || normalize)
    shared <- respondent_shares(data, category, facet, respondents)
    data <- shared$data
    value <- ".share"
    respondent_n <- shared$n
  }
  counted <- with_counts(data, value)
  check_columns(counted$data, c(category, counted$value, by, facet, color_by))
  stacked <- stacked && !is.null(by)
  divide <- percent || normalize
  percent <- divide || !is.null(respondents)
  if (!is.null(color_by) && is.null(by)) {
    stop("hairline: bars: color_by needs by =, the groups it colours", call. = FALSE)
  }
  check_bar_survey(show_n, header, inside, context, by, stacked, facet)
  check_labels(counted$data, c(by, facet), "bars")
  check_top(top, scales)
  groups <- if (is.null(by)) "" else group_names(counted$data[[by]])
  column <- identical(show_n, "column")
  options <- list(top = top, other = other %||% word("other"), show_n = !column && (isTRUE(show_n) || normalize),
                  context = as.character(context))
  panels <- facet_panels(counted$data, category, counted$value, by, facet, order,
                         sort %||% if (is.null(by) || stacked) "value" else "given", groups, options)
  every <- unique(unlist(lapply(panels, `[[`, "names")))
  check_partial(partial, every, "bars")
  check_context(as.character(context), every)
  columns <- columns %||% if (is.null(facet)) 1 else min(length(panels), 2)
  if ((column || !is.null(inside)) && isFALSE(horizontal)) {
    stop("hairline: bars: show_n = 'column' and inside = 'name' need horizontal bars", call. = FALSE)
  }
  if (column || !is.null(inside)) horizontal <- TRUE
  horizontal <- horizontal %||% bars_lie_down(panels, category, by, stacked, labels, percent, size %||% "onehalf",
                                              columns, divide)
  caption <- with_caption(caption, partial_caption(partial), if (!is.null(respondents)) word("several_answers"),
                          kept$note)
  drawn <- list(horizontal = horizontal, stacked = stacked, labels = labels, percent = percent, divide = divide,
                partial = partial, facet = facet, context = as.character(context), inside = inside,
                cap = if (!is.null(respondents)) 1 else Inf,
                coloured = bar_colours(counted$data, by, groups, color_by, colors, dimension))
  plot <- bar_plot(panels, counted, category, by, drawn) +
    ggplot2::labs(title = title %||% bars_title(counted$value, category, by), subtitle = subtitle, caption = caption,
                  x = NULL, y = NULL) + theme_hairline() +
    # Value labels may reach past the last break, as in Python, where they are never clipped.
    ggplot2::coord_cartesian(clip = "off")
  if (!is.null(facet)) {
    plot <- plot + ggplot2::facet_wrap(ggplot2::vars(.data$.facet), ncol = columns,
                                       scales = bar_facet_scales(scales, horizontal))
    for (entry in bar_facet_headers(panels, header, respondent_n)) plot <- plot + entry
  }
  if (percent) plot <- plot + if (horizontal) scale_x_hairline(percent = TRUE) else scale_y_hairline(percent = TRUE)
  if (column) plot@meta$hairline_side_numbers <- bar_side_numbers(panels)
  plot@meta$hairline_size <- size
  series <- if (is.null(by)) character() else unique(unname(drawn$coloured$series %||% groups))
  chart_options(plot, "bars", series, x_title = x_title, y_title = y_title, reference = reference,
                reference_axis = if (horizontal) "x" else "y", highlight = highlight, key_title = key_title)
}

# The bars of every panel (or, with `inside = "name"`, the named segments of one) on their category axis.
bar_plot <- function(panels, counted, category, by, options) {
  if (!is.null(options$inside)) {
    return(named_plot(ggplot2::ggplot(), panels[[1]], category, by, options$divide, options$percent))
  }
  built <- bar_frames(panels, category, by, options$horizontal, options$percent, options$stacked, options$facet,
                      options$partial, options$divide)
  ggplot2::ggplot() +
    bar_layers(built$frames, options$coloured$colours, options$horizontal, options$stacked, options$labels,
               options$percent, options$coloured$series, length(options$partial) > 0, options$context,
               options$cap) +
    bar_category_scale(options$horizontal, built$labels)
}
