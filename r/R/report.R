# Reports: figures and tables in order, numbered in the locale ("Abbildung 1", "Tabelle 2"), written as one
# self-contained Markdown or HTML file with the images embedded; the R twin of the Python package's report(). The
# rest of the document belongs to the document tool; this only keeps the numbering and captions right.

#' Numbered figures and tables in one file
#'
#' `hl_report()` starts a report; `hl_report_add()` adds a plot or a table
#' ([hl_table()]) with the sentence after its number (default: its title);
#' `hl_report_write()` writes it as Markdown (`.md`) or HTML (`.html`), every
#' image embedded, so the file stands alone. Figures and tables are numbered
#' apart, in the order added and in each plot's locale ("Figure 2",
#' "Tabelle 1"); an HTML report keeps tables as real `<table>`s.
#'
#' @param title Heading of the report.
#' @param dpi Resolution of the embedded images.
#' @param report A report from `hl_report()`.
#' @param plot A hairline plot or table.
#' @param caption The sentence after the number; `NULL` for the plot's title.
#' @param path File to write, ending in `.md` or `.html`.
#' @return `hl_report()` and `hl_report_add()` return the report; `hl_report_write()` returns `path` invisibly.
#' @examples
#' counts <- data.frame(Year = c("2024", "2025"), Cases = c(1841, 2010))
#' report <- hl_report("Quality report")
#' report <- hl_report_add(report, hl_table(counts, "Cases per year"))
#' hl_report_write(report, tempfile(fileext = ".html"))
#' @export
hl_report <- function(title = NULL, dpi = 200) {
  check_positive(dpi, "dpi")
  structure(list(title = title, dpi = dpi, items = list()), class = "hairline_report")
}

#' @rdname hl_report
#' @export
hl_report_add <- function(report, plot, caption = NULL) {
  check_report(report, "hl_report_add()")
  if (!S7::S7_inherits(plot, hairline_plot)) {
    stop("hairline: report: hl_report_add() takes a hairline plot or table", call. = FALSE)
  }
  report$items[[length(report$items) + 1]] <- list(plot = plot, caption = caption)
  report
}

check_report <- function(report, caller) {
  if (!inherits(report, "hairline_report")) {
    stop(sprintf("hairline: %s needs a report from hl_report()", caller), call. = FALSE)
  }
}

# Each item with its label ("Figure 2", "Tabelle 1") and caption, in the plot's own locale.
report_numbered <- function(report) {
  counts <- c(figure = 0, table = 0)
  lapply(report$items, function(item) {
    kind <- if (is.null(item$plot@meta$hairline_tabular)) "figure" else "table"
    counts[[kind]] <<- counts[[kind]] + 1
    locale <- item$plot@meta$hairline_settings$locale
    list(plot = item$plot, kind = kind, label = paste(word(kind, locale), counts[[kind]]),
         caption = item$caption %||% item$plot@labels$title %||% "")
  })
}

report_image <- function(plot, dpi) {
  base <- tempfile()
  on.exit(unlink(paste0(base, ".png")))
  hl_save(plot, base, formats = "png", dpi = dpi)
  path <- paste0(base, ".png")
  jsonlite::base64_enc(readBin(path, "raw", file.info(path)$size))
}

report_markdown <- function(report) {
  lines <- if (!is.null(report$title)) c(paste("#", report$title), "") else character()
  for (item in report_numbered(report)) {
    lines <- c(lines, sprintf("![%s](data:image/png;base64,%s)", html_escaped(item$label),
                              gsub("\n", "", report_image(item$plot, report$dpi))), "",
               sprintf("**%s.** %s", item$label, item$caption), "")
  }
  paste(lines, collapse = "\n")
}

report_html <- function(report) {
  parts <- if (!is.null(report$title)) sprintf("<h1>%s</h1>", html_escaped(report$title)) else character()
  for (item in report_numbered(report)) {
    caption <- sprintf("<figcaption><b>%s.</b> %s</figcaption>", html_escaped(item$label), html_escaped(item$caption))
    parts <- c(parts, if (item$kind == "table") {
      sprintf('<section class="hl-item">%s%s</section>', caption, table_html(item$plot))
    } else {
      sprintf(paste0('<figure class="hl-item"><img alt="%s" style="max-width:100%%" ',
                     'src="data:image/png;base64,%s">%s</figure>'),
              html_escaped(item$plot@labels$title %||% ""), gsub("\n", "", report_image(item$plot, report$dpi)),
              caption)
    })
  }
  paste0('<!doctype html>\n<html><head><meta charset="utf-8"><title>', html_escaped(report$title %||% "Report"),
         "</title><style>body{margin:0 auto;max-width:760px;padding:24px;font-family:sans-serif}",
         ".hl-item{margin:0 0 32px}figcaption{font-size:0.9em;margin-top:6px}</style></head><body>",
         paste(parts, collapse = ""), "</body></html>\n")
}

#' @rdname hl_report
#' @export
hl_report_write <- function(report, path) {
  check_report(report, "hl_report_write()")
  kind <- tolower(tools::file_ext(path))
  if (!kind %in% c("md", "html")) {
    stop(sprintf("hairline: report: hl_report_write() makes .md or .html files; got '%s'", basename(path)),
         call. = FALSE)
  }
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(if (kind == "md") report_markdown(report) else report_html(report), path, useBytes = TRUE)
  invisible(path)
}
