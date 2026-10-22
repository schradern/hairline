# Host integration, mirroring the Python package: a document editor hands hairline its
# context through a JSON file named by HAIRLINE_HOST_CONTEXT; hairline answers with figure files and a manifest.

host_environment <- "HAIRLINE_HOST_CONTEXT"
host_manifest <- "hairline-figures.json"
host_formats <- list(screen = "png", pdf = c("pdf", "png"), docx = c("pdf", "png"), html = c("svg", "png"))

# Warns once per file and problem; returns NULL, so a caller can return it as "no context" or "no value".
host_warn_once <- function(path, problem) {
  key <- paste(path, problem)
  if (key %in% hairline_state$host_warned) return(invisible())
  hairline_state$host_warned <- c(hairline_state$host_warned, key)
  warning(sprintf("hairline: host context %s: %s; continuing without it", path, problem), call. = FALSE)
  invisible(NULL)
}

# A context value as a warning shows it: text quoted, anything else formatted.
host_shown <- function(value) {
  if (is.character(value)) value <- sprintf("'%s'", value) else value <- format(value)
  paste(value, collapse = ", ")
}

# A size or resolution from the context: a number above zero, else warned about and left out.
host_positive <- function(path, value, key) {
  if (is.null(value)) return(NULL)
  if (!is.numeric(value) || length(value) != 1 || !is.finite(value) || value <= 0) {
    return(host_warn_once(path, sprintf("%s %s must be a number above zero", key, host_shown(value))))
  }
  value
}

# The context's locale as hairline names it ("de-DE" and "de_AT" are "de"); one hairline lacks is warned about and
# left out, so plots keep the session's locale.
host_locale <- function(path, value) {
  if (is.null(value)) return(NULL)
  locales <- names(hl_tokens()$locales)
  text <- is.character(value) && length(value) == 1
  if (text && value %in% locales) return(value)
  language <- if (text) tolower(strsplit(chartr("_", "-", value), "-")[[1]][1]) else NA
  if (!is.na(language) && language %in% locales) return(language)
  host_warn_once(path, sprintf("locale %s is not one of %s", host_shown(value), paste(sort(locales), collapse = ", ")))
}

# The file's content when it is a version-1 context with a known output, else NULL (warned once).
read_host_context <- function(path) {
  if (!file.exists(path)) return(host_warn_once(path, "the file does not exist"))
  content <- tryCatch(jsonlite::read_json(path, simplifyVector = TRUE), error = function(error) {
    host_warn_once(path, paste0("not valid JSON (", conditionMessage(error), ")"))
  })
  if (is.null(content)) return(NULL)
  version <- if (is.list(content)) content$version
  if (!identical(as.integer(version), 1L)) {
    return(host_warn_once(path, sprintf("version %s is not 1", format(version %||% "NULL"))))
  }
  output <- content$output %||% "screen"
  if (!output %in% names(host_formats)) {
    return(host_warn_once(path, sprintf("output '%s' must be one of %s", output,
                                        paste(names(host_formats), collapse = ", "))))
  }
  content
}

# A context from the file; values of the wrong kind are warned about and left out, the rest applies.
parse_host_context <- function(path) {
  content <- read_host_context(path)
  if (is.null(content)) return(NULL)
  output <- content$output %||% "screen"
  folder <- content$figure_dir
  if (!is.null(folder) && !(is.character(folder) && length(folder) == 1)) {
    folder <- host_warn_once(path, sprintf("figure_dir %s must be a folder path", host_shown(folder)))
  }
  design <- content$design
  if (!is.null(design) && !is.list(design)) {
    design <- host_warn_once(path, sprintf("design %s must be a mapping", host_shown(design)))
  }
  list(host = content$host %||% "host", output = output, brand = content$brand,
       width_mm = host_positive(path, content$width_mm, "width_mm"),
       interactive = isTRUE(content$interactive) && output == "html", locale = host_locale(path, content$locale),
       base_size = host_positive(path, content$base_size, "base_size"), figure_dir = folder,
       design = design %||% list(), dpi = host_positive(path, content$dpi, "dpi"))
}

# The current context, re-read when the variable points to another file. A new context re-applies the session's
# style (keeping the arguments passed to hl_use()), so a host that switches output, font or brand between runs of
# one long-lived session gets plots in the new style.
host_context <- function() {
  path <- Sys.getenv(host_environment)
  if (!nzchar(path)) return(NULL)
  if (!identical(path, hairline_state$host_path)) {
    hairline_state$host_path <- path
    hairline_state$host_context <- parse_host_context(path)
    if (!is.null(hairline_state$host_context)) {
      tryCatch(hl_reapply(), error = function(error) {
        host_warn_once(path, sprintf("its style could not be applied (%s)", conditionMessage(error)))
      })
    }
  }
  hairline_state$host_context
}

# Identifies a plot across builds (a built plot carries fresh environments, so it cannot be hashed whole).
host_plot_key <- function(plot) {
  layers <- lapply(plot@layers, function(layer) {
    list(class(layer$geom)[1], vapply(layer$mapping, rlang::quo_text, character(1)))
  })
  rlang::hash(list(plot@data, plot@labels, vapply(plot@mapping, rlang::quo_text, character(1)), layers))
}

# The figures already listed; a manifest that is not a list of figures is replaced, with a warning, so one damaged
# file does not stop every later figure.
read_host_manifest <- function(path) {
  if (!file.exists(path)) return(list())
  entries <- tryCatch(jsonlite::read_json(path, simplifyVector = FALSE), error = function(error) NULL)
  if (is.list(entries) && is.null(names(entries))) return(entries)
  warning(sprintf("hairline: host manifest %s is not a list of figures; starting a new one", path), call. = FALSE)
  list()
}

# Write a displayed plot to the host's folder in the formats its output needs and list it in the manifest; the
# current device stays the current device. Once per distinct plot and figure folder: a host that empties the
# folder between runs (the manifest is gone) gets a plot drawn again handed off again.
host_hand_off <- function(plot) {
  context <- host_context()
  if (is.null(context) || is.null(context$figure_dir) || isTRUE(hairline_state$handing_off)) return(invisible())
  if (!file.exists(file.path(context$figure_dir, host_manifest))) hairline_state$handed_off <- NULL
  key <- host_plot_key(plot)
  if (key %in% hairline_state$handed_off) return(invisible())
  hairline_state$handing_off <- TRUE
  device <- grDevices::dev.cur()
  on.exit({
    hairline_state$handing_off <- FALSE
    if (device > 1) grDevices::dev.set(device)
  })
  manifest_path <- file.path(context$figure_dir, host_manifest)
  entries <- read_host_manifest(manifest_path)
  figure_id <- sprintf("figure-%d", length(entries) + 1)
  dpi <- if (context$output == "screen" && !is.null(context$dpi)) context$dpi else hl_tokens()$export$dpi
  dir.create(context$figure_dir, recursive = TRUE, showWarnings = FALSE)
  formats <- c(host_formats[[context$output]], if (isTRUE(context$interactive)) "html")
  paths <- hl_save(plot, file.path(context$figure_dir, figure_id), formats = formats, dpi = dpi)
  size <- fitted_size_mm(plot, figure_size_mm("onehalf", NULL, plot@meta$hairline_height_mm))
  files <- stats::setNames(as.list(paths), tools::file_ext(paths))
  entries[[length(entries) + 1]] <- list(id = figure_id, files = files, width_mm = round(size[1], 2),
                                         height_mm = round(size[2], 2), alt = figure_alt(plot))
  jsonlite::write_json(entries, manifest_path, auto_unbox = TRUE, pretty = TRUE)
  hairline_state$handed_off <- c(hairline_state$handed_off, key)
  invisible(paths)
}
