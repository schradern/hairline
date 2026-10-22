# hl_save(): print-ready PDF, PNG, SVG and TIFF in one call.

# Known formats in the order given, each once, in any case ("PNG" is png).
validated_formats <- function(formats) {
  valid <- hl_tokens()$export$valid_formats
  formats <- unique(tolower(as.character(formats)))
  unknown <- setdiff(formats, valid)
  if (length(unknown) > 0) {
    stop(sprintf("hairline: unknown format '%s'; use one of %s", unknown[1], paste(valid, collapse = ", ")),
         call. = FALSE)
  }
  if (length(formats) == 0) stop("hairline: no output format given", call. = FALSE)
  formats
}

strip_known_extension <- function(name) {
  extension <- tolower(tools::file_ext(name))
  if (extension %in% hl_tokens()$export$valid_formats) sub(paste0("\\.", extension, "$"), "", name, ignore.case = TRUE)
  else name
}

# A size or resolution above zero; ragg crashes R on zero or negative ones.
check_positive <- function(value, name) {
  if (!is.null(value) && (!is.numeric(value) || length(value) != 1 || !is.finite(value) || value <= 0)) {
    stop(sprintf("hairline: %s must be a number above zero; got %s", name, paste(format(value), collapse = ", ")),
         call. = FALSE)
  }
}

# A raster beyond the pixel budget (about an A0 poster at 600 dpi) is refused before its buffer exists: its memory
# grows with width x height x dpi^2, so a size in the wrong unit or a stray dpi could fill the machine.
check_raster_size <- function(size_mm, dpi, format) {
  if (!format %in% c("png", "tiff")) return(invisible())
  megapixels <- prod(size_mm / 25.4 * dpi) / 1e6
  limit <- hl_tokens()$export$max_megapixels
  if (megapixels <= limit) return(invisible())
  stop(sprintf(paste("hairline: a %.0f x %.0f mm figure at %s dpi is %s megapixels, more than the %s a raster image",
                     "may have; lower the dpi or the size (in mm)"), size_mm[1], size_mm[2], format(dpi),
               format(round(megapixels), big.mark = ",", scientific = FALSE), format(limit, big.mark = ",")),
       call. = FALSE)
}

check_size_preset <- function(size) {
  presets <- names(hl_tokens()$sizes)
  if (!(is.character(size) && length(size) == 1 && size %in% presets)) {
    shown <- if (is.character(size)) sprintf("'%s'", size) else format(size)
    stop(sprintf("hairline: unknown size %s; use one of %s", paste(shown, collapse = ", "),
                 paste(sort(presets), collapse = ", ")), call. = FALSE)
  }
}

figure_size_mm <- function(size, width_mm, height_mm) {
  check_positive(width_mm, "width_mm")
  check_positive(height_mm, "height_mm")
  check_size_preset(size)
  preset <- hl_tokens()$sizes[[size]]
  width <- width_mm %||% host_context()$width_mm %||% preset$width_mm
  c(width, height_mm %||% preset$height_mm %||% (width * preset$aspect))
}

saved_settings <- function(plot, size) {
  settings <- plot@meta$hairline_settings %||% hl_settings()
  if (!isTRUE(settings$base_size_explicit)) settings$base_size <- hl_tokens()$sizes[[size]]$base_size
  settings
}

plot_for_size <- function(plot, size) {
  if (!S7::S7_inherits(plot, hairline_plot)) return(plot)
  settings <- saved_settings(plot, size)
  plot + theme_object(settings, axes = !isTRUE(plot@meta$hairline_bare))
}

format_device <- function(format, path, size_mm, dpi, background) {
  inches <- size_mm / 25.4
  switch(format,
         png = function() ragg::agg_png(path, size_mm[1], size_mm[2], units = "mm", res = dpi, background = background),
         tiff = function() {
           ragg::agg_tiff(path, size_mm[1], size_mm[2], units = "mm", res = dpi, background = background,
                          compression = "lzw")
         },
         svg = function() svglite::svglite(path, inches[1], inches[2], bg = background, fix_text_size = FALSE))
}

write_format <- function(plot, path, format, size_mm, dpi, background, size = "onehalf") {
  naming <- figure_name(plot)
  if (format == "pdf") return(write_pdf(plot, path, size_mm[1] / 25.4, size_mm[2] / 25.4, background, naming))
  if (format == "html") return(write_html(plot, path, size, size_mm, background))
  draw_to_device(format_device(format, path, size_mm, dpi, background), plot)
  name_file(path, format, naming)
}

#' Save print-ready files
#'
#' Writes `name.<format>` for each format: PDF (vector), PNG and TIFF (600 dpi
#' by default, TIFF LZW-compressed) and SVG (text kept as text). Every file
#' is named by the plot's title, with the title and subtitle as
#' their description; none shows a timestamp or producer banner. PDF uses cairo
#' where it is available; otherwise svglite + rsvg. Both embed the bundled font
#' once it can be found: cairo finds it on its own outside Windows, otherwise
#' run [hl_install_font()] once. PDFs are byte-identical across runs with
#' cairo before 1.17.6; later versions keep a creation date inside a
#' compressed stream that no PDF reader shows.
#'
#' @param plot A ggplot, ideally with [theme_hairline()].
#' @param name Output path without extension; parent folders are created.
#' @param formats Any of `"pdf"`, `"png"`, `"svg"`, `"tiff"`, `"html"` (the SVG with tooltips and series
#'   highlighting, self-contained).
#' @param size Size preset: `"single"` (85 mm), `"onehalf"` (120), `"double"` (174), `"a4"` (160), `"slide"`.
#' @param width_mm,height_mm Explicit size in mm; overrides the preset.
#' @param dpi Resolution for PNG and TIFF.
#' @param background `NULL` for the plot's background or `"transparent"`.
#' @return The written paths, invisibly.
#' @examples
#' plot <- ggplot2::ggplot(datasets::mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
#'   ggplot2::labs(title = "Fuel use by weight") + theme_hairline()
#' hl_save(plot, file.path(tempdir(), "fuel"), formats = "png", size = "single", dpi = 150)
#' @export
hl_save <- function(plot, name, formats = c("pdf", "png"), size = "onehalf", width_mm = NULL, height_mm = NULL,
                    dpi = 600, background = NULL) {
  formats <- validated_formats(formats)
  check_positive(dpi, "dpi")
  least <- hl_tokens()$export$min_dpi
  if (dpi < least) {
    stop(sprintf("hairline: dpi must be at least %s, below which text is smaller than a pixel; got %s", least, dpi),
         call. = FALSE)
  }
  check_size_preset(size)
  if (!(is.character(name) && length(name) == 1 && nzchar(name))) {
    stop(sprintf("hairline: name must be one file path; got %s", paste(format(name), collapse = ", ")), call. = FALSE)
  }
  if ("svg" %in% formats && !requireNamespace("svglite", quietly = TRUE)) {
    stop("hairline: SVG export needs the 'svglite' package", call. = FALSE)
  }
  plot <- plot_for_size(plot, size)
  size_mm <- fitted_size_mm(plot, figure_size_mm(size, width_mm, height_mm %||% plot@meta$hairline_height_mm))
  for (format in formats) check_raster_size(size_mm, dpi, format)
  surface <- if (identical(background, "transparent")) "transparent" else
    background %||% saved_settings(plot, size)$neutral$surface
  name <- strip_known_extension(name)
  dir.create(dirname(name), recursive = TRUE, showWarnings = FALSE)
  paths <- paste0(name, ".", formats)
  folders <- paths[dir.exists(paths)]
  if (length(folders)) {
    stop(sprintf("hairline: cannot write %s: a folder of that name exists", folders[1]), call. = FALSE)
  }
  partials <- hidden_path(paths, "partial")
  on.exit(unlink(partials), add = TRUE)
  for (index in seq_along(formats)) {
    tryCatch(write_format(plot, partials[index], formats[index], size_mm, dpi, surface, size), error = function(error) {
      stop(sprintf("hairline: writing %s failed: %s", paths[index], conditionMessage(error)), call. = FALSE)
    })
  }
  move_into_place(partials, paths)
  invisible(paths)
}

# A hidden sibling for each file while it is written or backed up, named so it never meets an existing file.
hidden_path <- function(paths, role) {
  vapply(paths, function(path) {
    tempfile(pattern = ".hairline-", tmpdir = dirname(path), fileext = paste0(".", tools::file_ext(path), ".", role))
  }, character(1), USE.NAMES = FALSE)
}

renamed <- function(from, to) suppressWarnings(file.rename(from, to))

# Every new file replaces its destination only once all are written; if one cannot be moved, the files moved before
# it get their old content back, so a failed save leaves every existing file as it was.
move_into_place <- function(partials, paths) {
  backups <- hidden_path(paths, "backup")
  existed <- file.exists(paths)
  moved <- 0L
  for (index in seq_along(paths)) {
    if (existed[index] && !renamed(paths[index], backups[index])) break
    if (!renamed(partials[index], paths[index])) {
      if (existed[index]) renamed(backups[index], paths[index])
      break
    }
    moved <- index
  }
  if (moved < length(paths)) {
    for (index in seq_len(moved)) if (existed[index]) renamed(backups[index], paths[index]) else unlink(paths[index])
    stop(sprintf("hairline: moving the new file into %s failed; existing files keep their old content",
                 paths[moved + 1L]), call. = FALSE)
  }
  unlink(backups[existed])
}
