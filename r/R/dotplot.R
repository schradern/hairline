# Dot plot with intervals, mirroring the Python dotplot(): sorted by value, labels on the left,
# the value on the right; drawn with the forest plot's geometry.

#' Dot plot with intervals
#'
#' One dot per row, largest at the top. With `low` and `high` each dot gets
#' its interval and the numbers on the right; `reference` adds a vertical line.
#'
#' @param data A data frame.
#' @param label,estimate Columns: row label and value.
#' @param low,high Interval columns, optional.
#' @param title,subtitle,caption Frame texts; the title defaults to the columns.
#' @param sort Sort by value, largest at the top.
#' @param ratio Values are ratios (log axis).
#' @param digits Decimals of the numbers; `NULL` gives two, or more for small or close values.
#' @param n Column holding each row's n, written after its label in the locale ("Medical (n = 1,010)").
#' @param percent `TRUE` draws shares (0.15) as percent (15), the heading naming the unit.
#' @param order Row order instead of sorting by value.
#' @param facet Column whose values each get a block of rows under their name, each block sorted on its own.
#' @param show_n `FALSE` leaves the n out of the labels (it still counts for `min_n`).
#' @param summary Take the rows as values and draw one row per label (per block with `facet`): a centre, `"median"`
#'   or `"mean"`, with an interval that belongs to it, `"iqr"` or `"range"` with the median, `"sd"`, `"ci"` or
#'   `"range"` with the mean (`summary = c("mean", "ci")`). Each row's n is counted, written after its label and
#'   used by `min_n`; the heading names the measures and the axis takes the column's name.
#' @param compare With `summary`: columns with each row's difference against one label (`compare = "Medical"`) or
#'   the row above (`"adjacent"`), its 95% CI and p, within each block; the caption names the test (Welch's t-test
#'   with the mean, the Hodges-Lehmann shift and Wilcoxon rank-sum test with the median).
#' @param numbers Where the numbers go: beside the intervals while they keep their least width, else under each
#'   row (`"auto"`), always beside them (`"right"`), or always under each row (`"below"`).
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' rates <- data.frame(unit = c("Medical", "Surgical", "Cardiac"), mortality = c(0.13, 0.08, 0.06),
#'                     low = c(0.11, 0.07, 0.04), high = c(0.15, 0.10, 0.08))
#' hl_dotplot(rates, "unit", "mortality", "low", "high")
#' @export
hl_dotplot <- function(data, label, estimate, low = NULL, high = NULL, title = NULL, subtitle = NULL, caption = NULL,
                       sort = TRUE, ratio = FALSE, reference = NULL, digits = NULL, n = NULL, percent = FALSE,
                       order = NULL, min_n = NULL, x_title = NULL, highlight = NULL, facet = NULL, show_n = TRUE,
                       summary = NULL, compare = NULL, numbers = "auto", reference_legend = FALSE) {
  check_columns(data, c(label, estimate, low, high, n, facet))
  if (is.null(low) != is.null(high)) {
    stop(sprintf("hairline: dotplot: an interval needs both low and high; got only %s = '%s'",
                 if (is.null(low)) "high" else "low", low %||% high), call. = FALSE)
  }
  if (isTRUE(percent)) data <- dotplot_percent(data, c(estimate, low, high))
  heading <- NULL
  raw <- data
  if (!is.null(compare) && is.null(summary)) {
    stop(paste("hairline: dotplot: compare needs summary =, so each row has the values it is compared on",
               "(summary = c(\"mean\", \"ci\"))"), call. = FALSE)
  }
  if (!is.null(summary)) {
    # Decimals as the other charts write a mean of these values: by magnitude, one more for whole numbers.
    values <- suppressWarnings(as.numeric(data[[estimate]]))
    values <- values[!is.na(values)]
    digits <- digits %||% (auto_digits(values) + if (is_whole(values)) 1 else 0)
    found <- dotplot_summarised(data, label, estimate, list(low, high, n), facet, summary)
    data <- found$data
    low <- found$low
    high <- found$high
    n <- found$n
    heading <- found$heading
    x_title <- x_title %||% if (isTRUE(percent)) paste0(humanise(estimate), " (%)") else humanise(estimate)
  }
  interval <- !is.null(low) && !is.null(high)
  kept <- dotplot_min_n(data, label, n, min_n)
  arranged <- dotplot_faceted(kept$data, label, estimate, sort, order, facet)
  data <- arranged$data
  names <- as.character(data[[label]])
  compared <- dotplot_comparisons(raw, data, names, arranged$blocks, c(label, estimate, facet), compare, summary,
                                  digits)
  data <- compared$data
  chosen <- checked_highlight(highlight, names, "dotplot")
  references <- legend_references(reference, reference_legend, "dotplot")
  if (!is.null(n)) check_numeric(data, n, "dotplot")
  if (!is.null(n) && isTRUE(show_n)) {
    data[[label]] <- labels_with_n(names, stats::setNames(as.list(data[[n]]), names))
  }
  if (!interval) {
    data$.low <- data[[estimate]]
    data$.high <- data[[estimate]]
    low <- ".low"
    high <- ".high"
  }
  name <- if (isTRUE(percent)) paste0(humanise(estimate), " (%)") else humanise(estimate)
  heading <- heading %||% if (interval) word("interval", name = name) else name
  spec <- forest_spec(data, label, estimate, low, high, ratio = ratio, colour = lone_colour(),
                      study_heading = humanise(label), effect_heading = heading, digits = digits, marker = "dot",
                      interval = interval, null = NULL, references = option_references(references$reference, "dotplot"),
                      axis_title = x_title, columns = compared$columns,
                      numbers = check_numbers(numbers, "dotplot"))
  spec$chart <- "dotplot"
  if (length(chosen)) {
    for (index in seq_along(spec$rows)) {
      spec$rows[[index]]$color <- if (names[index] %in% chosen) spec$color else context_colour()
    }
  }
  if (length(arranged$blocks)) spec$rows <- dotplot_headings(spec$rows, arranged$blocks)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(estimate), "by", gsub("_", " ", label)), subtitle = subtitle,
                  caption = with_caption(caption, c(kept$note, compared$note)), x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) forest_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_reference_legend <- references$labels
  plot
}

# With `compare`: each row's delta and p within its block as two text columns, the columns for the forest layout and
# the caption note naming the test; otherwise the rows as they are. As Python's dot_comparisons().
dotplot_comparisons <- function(raw, data, names, blocks, columns, compare, summary, digits) {
  if (is.null(compare)) return(list(data = data, columns = character(), note = NULL))
  label <- columns[1]
  estimate <- columns[2]
  facet <- if (length(columns) > 2) columns[3]
  blocked <- if (length(blocks)) blocks else rep("", length(names))
  keys <- paste0(blocked, "\u001f", names)
  within <- if (is.null(facet)) rep("", nrow(raw)) else as.character(raw[[facet]])
  labels <- as.character(raw[[label]])
  values <- stats::setNames(lapply(seq_along(keys), function(index) {
    found <- suppressWarnings(as.numeric(raw[[estimate]][within == blocked[index] & labels == names[index]]))
    found[!is.na(found)]
  }), keys)
  rows <- lapply(seq_along(keys), function(index) list(name = keys[index], section = blocked[index], pairs = list()))
  number <- function(value) hl_format_number(value, digits %||% 2)
  compared <- section_comparisons(rows, values, compare, check_summary(summary, "dotplot"), list(number, number),
                                  "dotplot", stats::setNames(names, keys))
  data$.hairline_difference <- vapply(compared$rows, function(row) row$pairs[[1]][2], character(1))
  data$.hairline_p <- vapply(compared$rows, function(row) row$pairs[[2]][2], character(1))
  headings <- stats::setNames(c(".hairline_difference", ".hairline_p"),
                              c(word("interval", name = word("difference")), "p"))
  list(data = data, columns = headings, note = compared$note)
}

# One row per label (per block and label with `facet`), in the order labels first appear: the centre as the
# estimate, the interval's ends and n; with the columns to read them from and the heading naming them. As Python's
# summarised().
dotplot_summarised <- function(data, label, estimate, given, facet, summary) {
  marks <- check_paired(check_summary(summary, "dotplot"), "dotplot")
  if (any(!vapply(given, is.null, logical(1)))) {
    stop(paste("hairline: dotplot: summary computes each row's centre, interval and n from the values; leave out",
               "low, high and n"), call. = FALSE)
  }
  check_labels(data, c(label, facet), "dotplot")
  check_numeric(data, estimate, "dotplot")
  keys <- if (is.null(facet)) as.character(data[[label]]) else
    paste(as.character(data[[facet]]), as.character(data[[label]]), sep = "\r")
  rows <- lapply(unique(keys), function(key) {
    part <- data[keys == key, , drop = FALSE]
    values <- as.numeric(stats::na.omit(part[[estimate]]))
    if (!length(values)) return(NULL)
    found <- summary_values(values)
    name <- as.character(part[[label]][1])
    if (!is.null(marks$interval) && marks$interval %in% c("sd", "ci") && !is.finite(found$sd)) {
      stop(sprintf("hairline: dotplot: '%s' has one value, and an %s needs two or more; min_n = 2 leaves such rows out",
                   name, toupper(marks$interval)), call. = FALSE)
    }
    ends <- if (is.null(marks$interval)) rep(found[[marks$centre]], 2) else interval_of(found, marks$interval)
    row <- data.frame(name, found[[marks$centre]], ends[1], ends[2], found$n)
    names(row) <- c(label, estimate, ".hairline_low", ".hairline_high", ".hairline_n")
    if (!is.null(facet)) row[[facet]] <- part[[facet]][1]
    row
  })
  heading <- if (is.null(marks$interval)) word(marks$centre) else
    word("summary_heading", centre = word(marks$centre), interval = word(summary_legend_words[[marks$interval]]))
  list(data = do.call(rbind, Filter(Negate(is.null), rows)),
       low = if (!is.null(marks$interval)) ".hairline_low", high = if (!is.null(marks$interval)) ".hairline_high",
       n = ".hairline_n", heading = heading)
}

# Rows whose `n` reaches `min_n`, and the caption note naming the others; `min_n` needs the n column. As Python's
# rows_with_min_n().
dotplot_min_n <- function(data, label, n, min_n) {
  if (is.null(min_n)) return(list(data = data, note = NULL))
  if (is.null(n)) stop("hairline: dotplot: min_n needs n =, the column holding each row's n", call. = FALSE)
  check_numeric(data, n, "dotplot")
  names <- as.character(data[[label]])
  dropped <- drop_small(stats::setNames(lapply(data[[n]], function(count) rep(1, count)), names), min_n, "dotplot")
  list(data = data[names %in% names(dropped$groups), , drop = FALSE], note = dropped$note)
}

# The rows in `order` when given, else largest first when sorted, else as given. As Python's ordered_rows().
dotplot_ordered <- function(data, label, estimate, sort, order) {
  if (!is.null(order)) {
    names <- ordered_names(data[[label]], order, "dotplot", label)
    return(data[match(names, as.character(data[[label]])), , drop = FALSE])
  }
  if (sort) data[order(-data[[estimate]], seq_len(nrow(data))), , drop = FALSE] else data
}

# The rows, block after block when faceted (each block ordered on its own), and each row's block. As Python's
# faceted_rows().
dotplot_faceted <- function(data, label, estimate, sort, order, facet) {
  if (is.null(facet)) return(list(data = dotplot_ordered(data, label, estimate, sort, order), blocks = character()))
  parts <- lapply(unique(as.character(data[[facet]])), function(block) {
    rows <- data[as.character(data[[facet]]) == block, , drop = FALSE]
    present <- as.character(order)[as.character(order) %in% as.character(rows[[label]])]
    dotplot_ordered(rows, label, estimate, sort, if (is.null(order)) NULL else present)
  })
  data <- do.call(rbind, parts)
  list(data = data, blocks = as.character(data[[facet]]))
}

# A heading row before the first row of each block. As Python's with_headings().
dotplot_headings <- function(rows, blocks) {
  found <- list()
  for (index in seq_along(rows)) {
    if (index == 1 || blocks[index] != blocks[index - 1]) {
      found[[length(found) + 1]] <- list(heading = blocks[index], study = blocks[index], cells = list(),
                                         effect_text = "", weight_text = "")
    }
    found[[length(found) + 1]] <- rows[[index]]
  }
  found
}

# Shares as percent: each named column x 100.
dotplot_percent <- function(data, columns) {
  check_numeric(data, columns, "dotplot")
  for (column in columns) data[[column]] <- data[[column]] * 100
  data
}
