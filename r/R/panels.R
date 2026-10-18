# Panel headers: name, qualifier and key numbers, moving the key numbers to a second line when they do not fit.

hairline_header <- S7::new_class("hairline_header", package = "hairline",
                                 properties = list(panel = S7::class_any, name = S7::class_any,
                                                   qualifier = S7::class_any, stats = S7::class_any,
                                                   key = S7::class_any, x_title = S7::class_any))

#' Panel header with key numbers
#'
#' Adds a header line above a panel: the name, an optional qualifier, and key
#' numbers right-aligned. When the numbers do not fit they move to a second
#' line; numbers that still do not fit are dropped with a warning.
#'
#' @param name Header name. For faceted plots, defaults to the facet label of `panel`.
#' @param qualifier Muted text after the name, e.g. `"24 beds"`.
#' @param stats Named character vector of key numbers, e.g. `c(Mean = "61.4%", Median = "61.3%")`.
#' @param panel Facet label the header belongs to; `NULL` for a single-panel plot.
#' @param key Name of the one key number to emphasise, e.g. `"Days over 90%"`.
#' @param x_title Title under this panel's own x-axis numbers, e.g. its unit when panels measure different things.
#' @return An object to add to a ggplot with `+`.
#' @examples
#' data <- data.frame(day = rep(1:10, 2), share = c(seq(0.6, 0.9, length.out = 10), rep(0.7, 10)),
#'                    unit = rep(c("Unit A", "Unit B"), each = 10))
#' ggplot2::ggplot(data, ggplot2::aes(day, share)) + ggplot2::geom_line() +
#'   ggplot2::facet_wrap(~unit) +
#'   ggplot2::labs(title = "Occupancy") + theme_hairline() +
#'   hl_panel_header(panel = "Unit A", qualifier = "12 beds", stats = c(Mean = "75 %")) +
#'   hl_panel_header(panel = "Unit B", qualifier = "8 beds", stats = c(Mean = "70 %"))
#' @export
hl_panel_header <- function(name = NULL, qualifier = NULL, stats = NULL, panel = NULL, key = NULL, x_title = NULL) {
  if (!is.null(stats) && (is.null(names(stats)) || any(!nzchar(names(stats))))) {
    stop("hairline: hl_panel_header(stats =) needs a named vector, e.g. c(Mean = \"61.4%\")", call. = FALSE)
  }
  if (!is.null(key) && !key %in% names(stats)) {
    stop(sprintf("hairline: key '%s' is not one of the key numbers: %s", key, paste(names(stats), collapse = ", ")),
         call. = FALSE)
  }
  hairline_header(panel = panel, name = name, qualifier = qualifier, stats = stats, key = key, x_title = x_title)
}

add_hairline_header <- function(object, plot, ...) {
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  key <- object@panel %||% object@name %||% ".single"
  headers <- plot@meta$hairline_headers %||% list()
  headers[[key]] <- list(name = object@name %||% object@panel, qualifier = object@qualifier, stats = object@stats,
                         key = object@key, x_title = object@x_title)
  plot@meta$hairline_headers <- headers
  plot
}

header_styles <- function(settings) {
  neutral <- settings$neutral
  list(name = role_style(settings, "panel"), letter = role_style(settings, "panel", 600, neutral$ink),
       qualifier = role_style(settings, "label", 400, neutral$faint),
       stat_label = role_style(settings, "label", 400, neutral$faint),
       stat_value = role_style(settings, "label", hl_tokens()$type$value_weight, neutral$muted),
       key_value = role_style(settings, "label", hl_tokens()$type$key_weight, neutral$ink))
}

header_gaps <- function(settings) {
  spacing <- hl_tokens()$spacing
  base <- settings$base_size
  list(qualifier = spacing$qualifier_gap * base, pair = spacing$stats_pair * base,
       stats_min = spacing$stats_pair * base, letter = spacing$panel_letter_gap * base)
}

value_style <- function(label, key, styles) if (identical(label, key)) styles$key_value else styles$stat_value

stat_pairs_width <- function(stats, styles, gap, key = NULL) {
  if (length(stats) == 0) return(0)
  widths <- vapply(seq_along(stats), function(index) {
    label_width <- text_width_pt(paste0(names(stats)[index], " "), styles$stat_label)
    label_width + text_width_pt(stats[[index]], value_style(names(stats)[index], key, styles))
  }, numeric(1))
  sum(widths) + gap * (length(widths) - 1)
}

stat_runs <- function(stats, x, line, styles, gap, key = NULL) {
  runs <- list()
  for (index in seq_along(stats)) {
    if (index > 1) x <- x + gap
    label <- paste0(names(stats)[index], " ")
    style <- value_style(names(stats)[index], key, styles)
    runs[[length(runs) + 1]] <- list(text = label, x = x, line = line, style = styles$stat_label)
    x <- x + text_width_pt(label, styles$stat_label)
    runs[[length(runs) + 1]] <- list(text = stats[[index]], x = x, line = line, style = style)
    x <- x + text_width_pt(stats[[index]], style)
  }
  runs
}

compose_header <- function(header, left, right, styles, gaps) {
  runs <- list(list(text = header$name, x = left, line = 0, style = styles$name))
  end <- left + text_width_pt(header$name, styles$name)
  if (!is.null(header$qualifier)) {
    runs[[2]] <- list(text = header$qualifier, x = end + gaps$qualifier, line = 0, style = styles$qualifier)
    end <- end + gaps$qualifier + text_width_pt(header$qualifier, styles$qualifier)
  }
  stats <- header$stats %||% character()
  key <- header$key
  composed <- list(runs = runs, lines = 1, dropped = character())
  if (length(stats) == 0) return(composed)
  if (end + gaps$stats_min + stat_pairs_width(stats, styles, gaps$pair, key) <= right) {
    start <- right - stat_pairs_width(stats, styles, gaps$pair, key)
    composed$runs <- c(runs, stat_runs(stats, start, 0, styles, gaps$pair, key))
    return(composed)
  }
  while (length(stats) > 0 && left + stat_pairs_width(stats, styles, gaps$pair, key) > right) {
    composed$dropped <- c(names(stats)[length(stats)], composed$dropped)
    stats <- stats[-length(stats)]
  }
  composed$runs <- c(runs, stat_runs(stats, left, 1, styles, gaps$pair, key))
  composed$lines <- if (length(stats) > 0) 2 else 1
  composed
}
