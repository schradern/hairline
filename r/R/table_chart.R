# Tables for documents: any data frame of text or numbers in hairline's typography, numbers formatted in the locale,
# written by hl_save() as PDF, PNG, SVG and as a real HTML table; the same rules as the table chart of the Python
# package.

table_aligns <- c("left", "right", "center")
# A formatted number or percentage as text ("1 841", "-0,5", "12 %"): aligned as a number.
number_text <- "^[\u2212-]?[0-9\u202f\u00a0 .,]*[0-9]([\u202f\u00a0 ]?%)?$"

# A column as text: numbers in the locale with the column's own decimals (counts whole), missing as a dash, text as
# it is.
column_texts <- function(values, digits) {
  if (is.numeric(values)) {
    places <- digits %||% auto_digits(values)
    return(vapply(as.numeric(values), hl_format_number, character(1), digits = places))
  }
  texts <- as.character(values)
  texts[is.na(values)] <- ""
  texts
}

# Numbers, or text that is a formatted number in every row (missing cells aside).
is_number_column <- function(values) {
  if (is.numeric(values)) return(TRUE)
  present <- as.character(values[!is.na(values)])
  present <- present[!present %in% c("", "\u2013")]
  length(present) > 0 && all(grepl(number_text, present, perl = TRUE))
}

# Numbers right, text left (the first column always left), unless `align` says otherwise: one alignment for every
# column, one per column, or a named vector for some columns.
column_aligns <- function(data, align) {
  found <- vapply(seq_along(data), function(index) {
    if (index > 1 && is_number_column(data[[index]])) "right" else "left"
  }, character(1))
  if (length(align) == 1 && is.null(names(align))) {
    found <- rep(align, length(found))
  } else if (!is.null(names(align))) {
    unknown <- setdiff(names(align), names(data))
    if (length(unknown)) {
      stop(sprintf("hairline: table: align names '%s', which is not a column; columns: %s", unknown[1],
                   paste(names(data), collapse = ", ")), call. = FALSE)
    }
    found[match(names(align), names(data))] <- unname(align)
  } else if (!is.null(align)) {
    if (length(align) != length(found)) {
      stop(sprintf("hairline: table: align gives %d alignments for %d columns", length(align), length(found)),
           call. = FALSE)
    }
    found <- as.character(align)
  }
  wrong <- setdiff(found, table_aligns)
  if (length(wrong)) {
    stop(sprintf("hairline: table: align '%s' must be one of %s", wrong[1], paste(table_aligns, collapse = ", ")),
         call. = FALSE)
  }
  found
}

# Rows to set in bold, by position (1 is the first body row) or by the text of their first column.
bold_positions <- function(data, bold_rows) {
  first <- as.character(data[[1]])
  vapply(bold_rows, function(row) {
    if (is.numeric(row)) {
      if (!(row >= 1 && row <= nrow(data) && row == round(row))) {
        stop(sprintf("hairline: table: bold_rows names row %s, but the table has %d rows", format(row), nrow(data)),
             call. = FALSE)
      }
      return(as.integer(row))
    }
    if (as.character(row) %in% first) return(match(as.character(row), first))
    stop(sprintf(paste("hairline: table: bold_rows names '%s', which is neither a row position nor a value of the",
                       "first column"), row), call. = FALSE)
  }, integer(1))
}

table_spec <- function(data, digits = NULL, align = NULL, bold_rows = NULL) {
  if (!is.data.frame(data) || !ncol(data)) {
    stop("hairline: table needs a data frame with at least one column", call. = FALSE)
  }
  if (!nrow(data)) stop("hairline: table: the data has no rows to show", call. = FALSE)
  places <- if (!is.null(names(digits))) digits else stats::setNames(rep(list(digits), ncol(data)), names(data))
  columns <- lapply(names(data), function(column) column_texts(data[[column]], places[[column]]))
  list(header = names(data), rows = lapply(seq_len(nrow(data)), function(row) vapply(columns, `[`, "", row)),
       align = column_aligns(data, align), bold = bold_positions(data, as.list(bold_rows)))
}

#' Table for documents
#'
#' Any data frame in hairline's typography: a header row between hairline
#' rules, numbers right-aligned in the locale (each column with its own
#' decimals, or `digits`), text left-aligned; leading pairs of spaces indent a
#' row, as in the table of [hl_describe()], which passes straight in. The
#' first column wraps when the table is wider than the figure. [hl_save()]
#' writes it as PDF, PNG and SVG, and as a real HTML `<table>`, which a
#' document tool that drops images or Markdown tables keeps as a table.
#'
#' @param data A data frame of text or numbers.
#' @param title,subtitle,caption Frame texts; the caption follows the footnotes.
#' @param footnotes Lines under the table, each on its own line, before the caption.
#' @param bold_rows Rows to set in bold: positions (1 is the first body row) or values of the first column.
#' @param align `"left"`, `"right"` or `"center"` for every column, one per column, or a named vector for some.
#' @param digits Decimals for number columns: one for all, or a named vector per column.
#' @param size Size preset, as in [hl_save()].
#' @return A ggplot with the hairline frame.
#' @examples
#' counts <- data.frame(Year = c("2024", "2025"), Cases = c(1841, 2010), Share = c("48 %", "52 %"))
#' hl_table(counts, "Cases per year", footnotes = "Share of both years.", bold_rows = "2025")
#' @export
hl_table <- function(data, title = NULL, subtitle = NULL, caption = NULL, footnotes = NULL, bold_rows = NULL,
                     align = NULL, digits = NULL, size = "onehalf") {
  check_size_preset(size)
  spec <- table_spec(data, digits, align, bold_rows)
  notes <- paste(c(footnotes, caption), collapse = "\n")
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% "Table", subtitle = subtitle, caption = if (nzchar(notes)) notes,
                  x = NULL, y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) table_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_tabular <- spec
  plot@meta$hairline_size <- size
  plot
}

html_escaped <- function(content) {
  gsub('"', "&quot;", gsub(">", "&gt;", gsub("<", "&lt;", gsub("&", "&amp;", content, fixed = TRUE), fixed = TRUE),
                           fixed = TRUE), fixed = TRUE)
}

css_number <- function(value) format(signif(value, 15), scientific = FALSE, trim = TRUE, drop0trailing = TRUE)

table_cell_html <- function(tag, content, align, bold, settings, rules) {
  stripped <- sub("^ +", "", content)
  level <- nchar(content) - nchar(stripped)
  indent <- if (level >= 2 && align == "left") sprintf("padding-left:%spt;", css_number(level %/% 2 *
                                                                                          settings$base_size)) else ""
  weight <- if (bold) sprintf("font-weight:%s;", rules$header_weight) else ""
  sprintf('<%s style="text-align:%s;%s%s">%s</%s>', tag, align, indent, weight, html_escaped(stripped), tag)
}

table_html_style <- function(settings, rules) {
  neutral <- settings$neutral
  rule <- sprintf("%spt solid %s", css_number(hl_tokens()$lines$axis * settings$base_size), neutral$axis)
  size <- function(role) css_number(role_size(settings, role))
  paste0(font_faces(settings$font),
         ".hl-table{font-family:'", settings$font, "',sans-serif;color:", neutral$ink, ";margin:0}",
         ".hl-table figcaption{font-size:", size("title"), "pt;font-weight:600}",
         ".hl-table .hl-subtitle{font-size:", size("subtitle"), "pt;color:", neutral$muted, ";margin:0.2em 0 0.8em}",
         ".hl-table table{border-collapse:collapse;font-size:", size("label"), "pt;font-variant-numeric:tabular-nums}",
         ".hl-table thead tr{border-top:", rule, ";border-bottom:", rule, "}",
         ".hl-table tbody tr:last-child{border-bottom:", rule, "}",
         ".hl-table th,.hl-table td{padding:0.35em ", css_number(rules$column_gap / 2 * settings$base_size),
         "pt;vertical-align:top}",
         ".hl-table .hl-notes{font-size:", size("caption"), "pt;color:", neutral$faint, "}",
         ".hl-table .hl-notes p{margin:0.3em 0}")
}

# The table as one self-contained <figure> with a real <table>, in hairline's font, sizes, inks and rules.
table_html <- function(plot) {
  spec <- plot@meta$hairline_tabular
  settings <- plot@meta$hairline_settings %||% hl_settings()
  rules <- hl_tokens()$table
  cell <- function(tag, content, index, bold) table_cell_html(tag, content, spec$align[index], bold, settings, rules)
  head <- paste(vapply(seq_along(spec$header), function(index) cell("th", spec$header[index], index, TRUE), ""),
                collapse = "")
  body <- paste(vapply(seq_along(spec$rows), function(row) {
    cells <- vapply(seq_along(spec$rows[[row]]), function(index) {
      cell("td", spec$rows[[row]][index], index, row %in% spec$bold)
    }, "")
    paste0("<tr>", paste(cells, collapse = ""), "</tr>")
  }, ""), collapse = "")
  lines <- strsplit(plot@labels$caption %||% "", "\n", fixed = TRUE)[[1]]
  notes <- paste0("<p>", html_escaped(lines[nzchar(lines)]), "</p>", collapse = "")
  subtitle <- if (is.null(plot@labels$subtitle)) "" else
    sprintf('<p class="hl-subtitle">%s</p>', html_escaped(plot@labels$subtitle))
  paste0('<figure class="hl-table"><style>', table_html_style(settings, rules), "</style><figcaption>",
         html_escaped(plot@labels$title %||% ""), "</figcaption>", subtitle, "<table><thead><tr>", head,
         "</tr></thead><tbody>", body, '</tbody></table><div class="hl-notes">', if (length(lines)) notes else "",
         "</div></figure>")
}
