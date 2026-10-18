# hl_save(): print-ready PDF, PNG, SVG and TIFF in one call.

validated_formats <- function(formats) {
  valid <- hl_tokens()$export$valid_formats
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

figure_size_mm <- function(size, width_mm, height_mm) {
  presets <- hl_tokens()$sizes
  if (!size %in% names(presets)) {
    stop(sprintf("hairline: unknown size '%s'; use one of %s", size, paste(sort(names(presets)), collapse = ", ")),
         call. = FALSE)
  }
  preset <- presets[[size]]
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
  if (format == "pdf") return(write_pdf(plot, path, size_mm[1] / 25.4, size_mm[2] / 25.4, background))
  if (format == "html") return(write_html(plot, path, size, size_mm, background))
  draw_to_device(format_device(format, path, size_mm, dpi, background), plot)
}

#' Save print-ready files
#'
#' Writes `name.<format>` for each format: PDF (vector), PNG and TIFF (600 dpi
#' by default, TIFF LZW-compressed) and SVG (text kept as text). Output carries
#' no timestamps or producer banners. PDF uses cairo where it is available
#' (byte-identical across runs); otherwise svglite + rsvg, which is not
#' byte-stable and needs [hl_install_font()] to embed the bundled font.
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
#' @export
hl_save <- function(plot, name, formats = c("pdf", "png"), size = "onehalf", width_mm = NULL, height_mm = NULL,
                    dpi = 600, background = NULL) {
  formats <- validated_formats(formats)
  if ("svg" %in% formats && !requireNamespace("svglite", quietly = TRUE)) {
    stop("hairline: SVG export needs the 'svglite' package", call. = FALSE)
  }
  plot <- plot_for_size(plot, size)
  size_mm <- fitted_size_mm(plot, figure_size_mm(size, width_mm, height_mm %||% plot@meta$hairline_height_mm))
  surface <- if (identical(background, "transparent")) "transparent" else
    background %||% saved_settings(plot, size)$neutral$surface
  name <- strip_known_extension(name)
  dir.create(dirname(name), recursive = TRUE, showWarnings = FALSE)
  paths <- paste0(name, ".", formats)
  for (index in seq_along(formats)) {
    partial <- file.path(dirname(paths[index]), paste0(".", basename(paths[index]), ".partial"))
    tryCatch({
      write_format(plot, partial, formats[index], size_mm, dpi, surface, size)
      file.rename(partial, paths[index])
    }, error = function(error) {
      unlink(c(partial, paths[seq_len(index - 1)]))
      stop(sprintf("hairline: writing %s failed: %s", paths[index], conditionMessage(error)), call. = FALSE)
    })
  }
  invisible(paths)
}
