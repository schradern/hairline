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
#' @inheritParams chart_option_params
#' @return A ggplot with the hairline frame.
#' @examples
#' rates <- data.frame(unit = c("Medical", "Surgical", "Cardiac"), mortality = c(0.13, 0.08, 0.06),
#'                     low = c(0.11, 0.07, 0.04), high = c(0.15, 0.10, 0.08))
#' hl_dotplot(rates, "unit", "mortality", "low", "high")
#' @export
hl_dotplot <- function(data, label, estimate, low = NULL, high = NULL, title = NULL, subtitle = NULL, caption = NULL,
                       sort = TRUE, ratio = FALSE, reference = NULL, digits = NULL, n = NULL, percent = FALSE,
                       order = NULL, min_n = NULL, x_title = NULL, highlight = NULL) {
  check_columns(data, c(label, estimate, low, high, n))
  if (is.null(low) != is.null(high)) {
    stop(sprintf("hairline: dotplot: an interval needs both low and high; got only %s = '%s'",
                 if (is.null(low)) "high" else "low", low %||% high), call. = FALSE)
  }
  interval <- !is.null(low) && !is.null(high)
  if (isTRUE(percent)) data <- dotplot_percent(data, c(estimate, low, high))
  kept <- dotplot_min_n(data, label, n, min_n)
  data <- dotplot_ordered(kept$data, label, estimate, sort, order)
  names <- as.character(data[[label]])
  chosen <- checked_highlight(highlight, names, "dotplot")
  if (!is.null(n)) {
    check_numeric(data, n, "dotplot")
    data[[label]] <- labels_with_n(names, stats::setNames(as.list(data[[n]]), names))
  }
  if (!interval) {
    data$.low <- data[[estimate]]
    data$.high <- data[[estimate]]
    low <- ".low"
    high <- ".high"
  }
  name <- if (isTRUE(percent)) paste0(humanise(estimate), " (%)") else humanise(estimate)
  heading <- if (interval) word("interval", name = name) else name
  spec <- forest_spec(data, label, estimate, low, high, ratio = ratio, colour = lone_colour(),
                      study_heading = humanise(label), effect_heading = heading, digits = digits, marker = "dot",
                      interval = interval, null = NULL, references = option_references(reference, "dotplot"),
                      axis_title = x_title)
  if (length(chosen)) {
    for (index in seq_along(spec$rows)) {
      spec$rows[[index]]$color <- if (names[index] %in% chosen) spec$color else context_colour()
    }
  }
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste(humanise(estimate), "by", gsub("_", " ", label)), subtitle = subtitle,
                  caption = with_caption(caption, kept$note), x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) forest_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
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

# Shares as percent: each named column x 100.
dotplot_percent <- function(data, columns) {
  check_numeric(data, columns, "dotplot")
  for (column in columns) data[[column]] <- data[[column]] * 100
  data
}
