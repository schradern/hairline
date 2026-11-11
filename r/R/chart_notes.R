# Options charts share from use in reports: colour by a coarser column, the n after a label, notes in the caption
# (incomplete periods, groups too small to draw, values clipped off); the same rules as the common chart helpers of
# the Python package.

# Each group's value of a coarser column (`color_by`): a group that spans two values of it cannot take one colour, so
# that is refused.
coarse_groups <- function(data, group, coarse, chart) {
  check_columns(data, coarse)
  check_labels(data, coarse, chart)
  labels <- if (is.null(group)) rep("", nrow(data)) else as.character(data[[group]])
  values <- as.character(data[[coarse]])
  found <- character()
  for (name in unique(labels)) {
    distinct <- unique(values[labels == name])
    if (length(distinct) > 1) {
      stop(sprintf("hairline: %s: color_by '%s' gives '%s' more than one value (%s); every group needs one value of it",
                   chart, coarse, name, paste(utils::head(distinct, 3), collapse = ", ")), call. = FALSE)
    }
    found[[name]] <- distinct[1]
  }
  found
}

# "Sepsis (n = 120)": the n after the label, in the locale; colours and order keep keying on the bare name.
labels_with_n <- function(names, counts, locale = NULL) {
  vapply(names, function(name) {
    paste0(name, " (", word("n_equals", locale, n = hl_format_number(counts[[name]], 0, locale)), ")")
  }, character(1), USE.NAMES = FALSE)
}

# The caption with hairline's own notes (incomplete periods, groups not shown, hidden values) after it.
with_caption <- function(caption, ...) {
  parts <- unlist(c(list(caption), list(...)))
  parts <- parts[!is.na(parts) & nzchar(parts)]
  if (length(parts)) paste(parts, collapse = " ") else NULL
}

# "Incomplete, drawn lighter: 2021 (2 months), 2026 (10 months)." in the locale.
partial_caption <- function(partial, locale = NULL) {
  if (!length(partial)) return(NULL)
  word("partial", locale, items = listed(paste0(names(partial), " (", unlist(partial), ")")))
}

check_partial <- function(partial, names, chart) {
  if (length(partial) && is.null(names(partial))) {
    stop(sprintf("hairline: %s: partial needs category names, such as c(\"2021\" = \"2 months\")", chart),
         call. = FALSE)
  }
  unknown <- setdiff(names(partial), names)
  if (length(unknown)) {
    stop(sprintf("hairline: %s: partial names '%s', which is not a category; categories: %s", chart, unknown[1],
                 paste(names, collapse = ", ")), call. = FALSE)
  }
}

check_min_n <- function(min_n, chart) {
  whole <- is.numeric(min_n) && length(min_n) == 1 && is.finite(min_n) && min_n >= 1 && min_n == round(min_n)
  if (!is.null(min_n) && !whole) {
    stop(sprintf("hairline: %s: min_n must be a whole number of 1 or more; got %s", chart,
                 paste(format(min_n), collapse = ", ")), call. = FALSE)
  }
}

# Groups (a named list of values) with fewer than `min_n` values are not drawn (a distribution of one value says
# nothing); the caption names them. All of them too small is an error, as an empty chart would be.
drop_small <- function(groups, min_n, chart, locale = NULL) {
  check_min_n(min_n, chart)
  if (is.null(min_n)) return(list(groups = groups, note = NULL))
  small <- lengths(groups) < min_n
  if (all(small)) {
    stop(sprintf("hairline: %s: every group has fewer than min_n=%d values; lower min_n", chart, as.integer(min_n)),
         call. = FALSE)
  }
  note <- if (any(small)) word("not_shown", locale, n = hl_format_number(min_n, 0, locale),
                               items = listed(names(groups)[small])) else NULL
  list(groups = groups[!small], note = note)
}

# The range drawn: everything (NULL), up to the `clip` quantile of every value (0.99: the top 1 % hidden), or between
# two values (`c(low, high)`, either NA for no limit there).
clip_limits <- function(values, clip, chart) {
  if (is.null(clip)) return(c(-Inf, Inf))
  if (length(clip) == 2) {
    limits <- c(if (is.na(clip[1])) -Inf else as.numeric(clip[1]), if (is.na(clip[2])) Inf else as.numeric(clip[2]))
    if (!(limits[1] < limits[2])) {
      stop(sprintf("hairline: %s: clip needs low below high; got %s", chart, paste(format(clip), collapse = ", ")),
           call. = FALSE)
    }
    return(limits)
  }
  if (!is.numeric(clip) || length(clip) != 1 || is.logical(clip) || !(clip > 0 && clip < 1)) {
    stop(sprintf("hairline: %s: clip must be a quantile between 0 and 1 (0.99) or c(low, high); got %s", chart,
                 paste(format(clip), collapse = ", ")), call. = FALSE)
  }
  c(-Inf, density_quantiles(values, clip))
}

# "3 values above 2,400 not drawn; the statistics use every value." in the locale; NULL when none is hidden.
clip_caption <- function(values, limits, clip_stats, locale = NULL) {
  hidden <- sum(values < limits[1] | values > limits[2])
  if (!hidden) return(NULL)
  digits <- auto_digits(values)
  shown <- vapply(limits, hl_format_number, character(1), digits = digits, locale = locale)
  where <- if (all(is.finite(limits))) word("outside", locale, low = shown[1], high = shown[2]) else
    if (is.finite(limits[2])) word("above", locale, limit = shown[2]) else word("below", locale, limit = shown[1])
  stats <- word(if (clip_stats) "stats_drawn" else "stats_every", locale)
  sentence <- word("clipped", locale, values = value_count_text(hidden, locale), where = where, stats = stats)
  paste0(toupper(substr(sentence, 1, 1)), substring(sentence, 2))
}

within_limits <- function(values, limits) values[values >= limits[1] & values <= limits[2]]

# Each group's colour and the legend label it stands for: its own name, or with `color_by` the coarser column's value
# (12 rows of procedure x age coloured by the 4 procedures; the palette counts the 4).
# `named`: the groups are named on an axis, so more groups than the palette has colours are all drawn in one colour.
series_colours <- function(names, data, group, color_by, colors, dimension, chart, highlight = NULL, named = FALSE) {
  if (named && is.null(colors) && is.null(color_by) && length(unique(names)) > length(hl_palette())) {
    colours <- stats::setNames(rep(lone_colour(), length(names)), names)
    return(list(palette = highlighted_colours(colours, highlight, names, chart), coarse = stats::setNames(names, names)))
  }
  coarse <- if (is.null(color_by)) stats::setNames(names, names) else coarse_groups(data, group, color_by, chart)
  palette <- colours_for(unique(unname(coarse[names])), colors, dimension)
  colours <- stats::setNames(unname(palette[coarse[names]]), names)
  list(palette = highlighted_colours(colours, highlight, names, chart),
       coarse = stats::setNames(unname(coarse[names]), names))
}

# Legend items for groups coloured by a coarser column: each coarser value once, in its colour.
coarse_legend <- function(coloured) {
  labels <- unname(coloured$coarse)
  first <- !duplicated(labels)
  lapply(which(first), function(index) {
    list(kind = "square", colour = unname(coloured$palette[index]), label = labels[index])
  })
}
