# Sankey, mirroring the Python sankey(): flows through two or more columns, links coloured by
# the group of one column.

sankey_check <- function(data, columns, value) {
  if (length(columns) < 2) {
    stop(sprintf("hairline: sankey needs at least two columns; got %s",
                 if (length(columns)) paste(columns, collapse = ", ") else "none"), call. = FALSE)
  }
  for (index in seq_len(nrow(data))) {
    if (!is.na(data[[value]][index]) && data[[value]][index] < 0) {
      path <- paste(vapply(columns, function(column) as.character(data[[column]][index]), character(1)),
                    collapse = " \u2192 ")
      stop(sprintf("hairline: sankey: %s has a negative value (%s); flows need values of zero or more", path,
                   format(data[[value]][index])), call. = FALSE)
    }
  }
}

sankey_links <- function(data, columns, value, group) {
  keys <- character()
  links <- list()
  for (row in which(!is.na(data[[value]]))) {
    for (index in seq_len(length(columns) - 1)) {
      source <- as.character(data[[columns[index]]][row])
      target <- as.character(data[[columns[index + 1]]][row])
      link_group <- if (is.null(group)) "" else as.character(data[[group]][row])
      key <- paste(index - 1, source, target, link_group, sep = "\r")
      if (!key %in% keys) {
        keys <- c(keys, key)
        links[[key]] <- list(column = index - 1, source = source, target = target, group = link_group, value = 0)
      }
      links[[key]]$value <- links[[key]]$value + data[[value]][row]
    }
  }
  unname(Filter(function(link) link$value > 0, links))
}

link_total <- function(links, column, end, name) {
  sum(vapply(links, function(link) if (link$column == column && link[[end]] == name) link$value else 0, numeric(1)))
}

sankey_nodes <- function(data, columns, links, color_column, palette, digits = 0) {
  muted <- hl_settings()$neutral$muted
  lapply(seq_along(columns), function(index) {
    nodes <- list()
    for (name in unique(as.character(data[[columns[index]]]))) {
      incoming <- link_total(links, index - 2, "target", name)
      outgoing <- link_total(links, index - 1, "source", name)
      amount <- max(incoming, outgoing)
      if (amount <= 0) next
      colour <- if (identical(index, color_column) && name %in% names(palette)) palette[[name]] else muted
      nodes[[length(nodes) + 1]] <- list(name = name, value = amount, value_text = hl_format_number(amount, digits),
                                         color = colour)
    }
    nodes
  })
}

sankey_spec <- function(data, columns, value, color_by = NULL, headings = NULL, colors = NULL) {
  check_columns(data, c(columns, value))
  group <- if (identical(color_by, "none")) NULL else color_by %||% columns[length(columns)]
  if (!is.null(group)) check_columns(data, group)
  check_labels(data, c(columns, group), "sankey")
  sankey_check(data, columns, value)
  if (!is.null(headings) && length(headings) != length(columns)) {
    stop(sprintf("hairline: sankey: %d heading(s) for %d columns; give one per column", length(headings),
                 length(columns)), call. = FALSE)
  }
  links <- sankey_links(data, columns, value, group)
  if (!length(links)) stop(sprintf("hairline: sankey: no flows above zero to draw in '%s'", value), call. = FALSE)
  color_column <- if (!is.null(group) && group %in% columns) match(group, columns) else NULL
  groups <- unique(vapply(links, `[[`, character(1), "group"))
  palette <- if (is.null(group)) character() else colours_for(groups, colors)
  nodes <- sankey_nodes(data, columns, links, color_column, palette,
                        auto_digits(vapply(links, `[[`, numeric(1), "value")))
  faint <- hl_settings()$neutral$faint
  links <- lapply(links, function(link) c(link, color = if (is.null(group)) faint else palette[[link$group]]))
  list(headings = as.list(headings %||% columns), nodes = nodes, links = links,
       groups = unique(vapply(links, `[[`, character(1), "group")))
}

#' Sankey diagram
#'
#' Flows from left to right through two or more columns. Nodes share one
#' scale; later columns are ordered to reduce crossings and links are ordered
#' at both ends, so they never cross inside a node. Links take the colour of
#' their group in `color_by` (default the last column).
#'
#' @param data A data frame, one row per path with its value.
#' @param columns The columns, left to right.
#' @param value Column with the amounts; `NULL` counts rows.
#' @param title,subtitle,caption Frame texts.
#' @param color_by Column whose groups colour the links, or `"none"`.
#' @param headings Column headings; default the column names.
#' @param colors Named colours for this chart only, e.g. `c(Male = "#0a6ddd")`; they override the colour set
#'   for the number of groups and are not remembered for other charts.
#' @return A ggplot with the hairline frame.
#' @examples
#' budget <- data.frame(income = c("Salary", "Salary", "Benefit"),
#'                      account = c("Joint", "Joint", "Savings"),
#'                      spending = c("Rent", "Food", "Reserve"), euros = c(1200, 420, 150))
#' hl_sankey(budget, c("income", "account", "spending"), "euros")
#' @export
hl_sankey <- function(data, columns, value = NULL, title = NULL, subtitle = NULL, caption = NULL, color_by = NULL,
                      headings = NULL, colors = NULL) {
  counted <- with_counts(data, value)
  data <- counted$data
  value <- counted$value
  title <- title %||% paste(humanise(value), "from", joined(columns[1]), "to", joined(columns[length(columns)]))
  spec <- sankey_spec(data, columns, value, color_by, headings %||% humanise(columns), colors)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title, subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) sankey_drawing(spec, box, measure, style)
  plot
}
