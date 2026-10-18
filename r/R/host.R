# Host integration, mirroring the Python package: a document editor hands hairline its
# context through a JSON file named by HAIRLINE_HOST_CONTEXT; hairline answers with figure files and a manifest.

host_environment <- "HAIRLINE_HOST_CONTEXT"
host_manifest <- "hairline-figures.json"
host_formats <- list(screen = "png", pdf = c("pdf", "png"), docx = c("pdf", "png"), html = c("svg", "png"))

host_warn_once <- function(path, problem) {
  key <- paste(path, problem)
  if (key %in% hairline_state$host_warned) return(invisible())
  hairline_state$host_warned <- c(hairline_state$host_warned, key)
  warning(sprintf("hairline: host context %s: %s; continuing without it", path, problem), call. = FALSE)
}

parse_host_context <- function(path) {
  if (!file.exists(path)) return(host_warn_once(path, "the file does not exist"))
  content <- tryCatch(jsonlite::read_json(path, simplifyVector = TRUE), error = function(error) {
    host_warn_once(path, paste0("not valid JSON (", conditionMessage(error), ")"))
    NULL
  })
  if (is.null(content)) return(NULL)
  if (!identical(as.integer(content$version), 1L)) {
    return(host_warn_once(path, sprintf("version %s is not 1", format(content$version %||% "NULL"))))
  }
  output <- content$output %||% "screen"
  if (!output %in% names(host_formats)) {
    return(host_warn_once(path, sprintf("output '%s' must be one of %s", output,
                                        paste(names(host_formats), collapse = ", "))))
  }
  list(host = content$host %||% "host", output = output, brand = content$brand, width_mm = content$width_mm,
       interactive = isTRUE(content$interactive) && output == "html", locale = content$locale,
       base_size = content$base_size, figure_dir = content$figure_dir, design = content$design %||% list(),
       dpi = content$dpi)
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
    if (!is.null(hairline_state$host_context)) hl_reapply()
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
  entries <- if (file.exists(manifest_path)) jsonlite::read_json(manifest_path, simplifyVector = FALSE) else list()
  figure_id <- sprintf("figure-%d", length(entries) + 1)
  dpi <- if (context$output == "screen" && !is.null(context$dpi)) context$dpi else hl_tokens()$export$dpi
  dir.create(context$figure_dir, recursive = TRUE, showWarnings = FALSE)
  formats <- c(host_formats[[context$output]], if (isTRUE(context$interactive)) "html")
  paths <- hl_save(plot, file.path(context$figure_dir, figure_id), formats = formats, dpi = dpi)
  size <- fitted_size_mm(plot, figure_size_mm("onehalf", NULL, plot@meta$hairline_height_mm))
  labels <- c(plot@labels$title, plot@labels$subtitle)
  files <- stats::setNames(as.list(paths), tools::file_ext(paths))
  entries[[length(entries) + 1]] <- list(id = figure_id, files = files, width_mm = round(size[1], 2),
                                         height_mm = round(size[2], 2), alt = paste(labels, collapse = ". "))
  jsonlite::write_json(entries, manifest_path, auto_unbox = TRUE, pretty = TRUE)
  hairline_state$handed_off <- c(hairline_state$handed_off, key)
  invisible(paths)
}
