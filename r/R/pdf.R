# PDF output: cairo_pdf with fontconfig pointed at the bundled font, or svglite + rsvg where cairo is missing.

cairo_works <- function() {
  if (is.null(hairline_state$cairo_works)) {
    hairline_state$cairo_works <- tryCatch({
      path <- tempfile(fileext = ".pdf")
      grDevices::cairo_pdf(path)
      grDevices::dev.off()
      unlink(path)
      TRUE
    }, error = function(error) FALSE, warning = function(warning) FALSE)
  }
  hairline_state$cairo_works
}

pdf_route <- function() {
  if (cairo_works()) return("cairo")
  if (requireNamespace("rsvg", quietly = TRUE) && requireNamespace("svglite", quietly = TRUE)) return("rsvg")
  "none"
}

font_installed_for_pdf <- function() hl_tokens()$font$family %in% systemfonts::system_fonts()$family

fontconfig_file <- function() {
  path <- file.path(tempdir(), "hairline-fonts.conf")
  if (!file.exists(path)) {
    writeLines(c("<?xml version=\"1.0\"?>", "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">", "<fontconfig>",
                 "<include ignore_missing=\"yes\">/etc/fonts/fonts.conf</include>",
                 "<include ignore_missing=\"yes\">/opt/homebrew/etc/fonts/fonts.conf</include>",
                 "<include ignore_missing=\"yes\">/usr/local/etc/fonts/fonts.conf</include>",
                 sprintf("<dir>%s</dir>", system.file("fonts", package = "hairline")),
                 sprintf("<cachedir>%s</cachedir>", file.path(tempdir(), "hairline-fontcache")), "</fontconfig>"),
               path)
  }
  path
}

draw_to_device <- function(open_device, plot) {
  open_device()
  on.exit(grDevices::dev.off())
  print(plot)
}

write_pdf <- function(plot, path, width_in, height_in, background, naming = NULL) {
  route <- pdf_route()
  if (route == "none") {
    stop("hairline: PDF export needs a working cairo device or the 'rsvg' and 'svglite' packages", call. = FALSE)
  }
  if (route == "cairo") {
    previous <- Sys.getenv("FONTCONFIG_FILE", unset = NA)
    Sys.setenv(FONTCONFIG_FILE = fontconfig_file())
    on.exit(if (is.na(previous)) Sys.unsetenv("FONTCONFIG_FILE") else Sys.setenv(FONTCONFIG_FILE = previous))
    draw_to_device(function() grDevices::cairo_pdf(path, width_in, height_in, bg = background), plot)
  } else {
    svg <- tempfile(fileext = ".svg")
    on.exit(unlink(svg))
    draw_to_device(function() svglite::svglite(svg, width_in, height_in, bg = background, fix_text_size = FALSE), plot)
    rsvg::rsvg_pdf(svg, path)
  }
  strip_pdf_metadata(path)
  set_pdf_info(path, naming)
  warn_missing_pdf_font(path)
}

strip_pdf_metadata <- function(path) {
  bytes <- readBin(path, "raw", file.size(path))
  reference <- grepRaw("/Info [0-9]+ 0 R", bytes, value = TRUE, all = TRUE)
  if (length(reference) == 0) return(invisible(path))
  number <- sub("/Info ([0-9]+) 0 R", "\\1", rawToChar(reference[[length(reference)]]))
  start <- grepRaw(sprintf("[\r\n]%s 0 obj", number), bytes)
  if (length(start) == 0) return(invisible(path))
  open <- grepRaw("<<", bytes, offset = start)
  close <- grepRaw(">>", bytes, offset = open + 2)
  if (length(open) && length(close) && close > open + 2) bytes[(open + 2):(close - 1)] <- as.raw(0x20)
  writeBin(bytes, path)
  invisible(path)
}

# Whether `text` occurs in the PDF, in its plain bytes or inside a compressed stream: cairo 1.17.6 and later keep
# font names and metadata in compressed object streams.
pdf_contains <- function(bytes, text) {
  if (length(grepRaw(text, bytes, fixed = TRUE))) return(TRUE)
  for (start in grepRaw("stream", bytes, fixed = TRUE, all = TRUE)) {
    if (start > 3 && identical(rawToChar(bytes[(start - 3):(start - 1)]), "end")) next
    body <- start + 6
    if (body <= length(bytes) && bytes[body] == as.raw(0x0d)) body <- body + 1
    if (body <= length(bytes) && bytes[body] == as.raw(0x0a)) body <- body + 1
    end <- grepRaw("endstream", bytes, offset = body, fixed = TRUE)
    if (length(end) == 0 || end <= body) next
    inflated <- tryCatch(memDecompress(bytes[body:(end - 1)], type = "gzip"), error = function(error) NULL)
    if (!is.null(inflated) && length(grepRaw(text, inflated, fixed = TRUE))) return(TRUE)
  }
  FALSE
}

# cairo 1.17.6 and later write object streams, where the creation date cannot be blanked in place.
pdf_has_object_streams <- function(bytes) length(grepRaw("/ObjStm", bytes, fixed = TRUE)) > 0

warn_missing_pdf_font <- function(path) {
  bytes <- readBin(path, "raw", file.size(path))
  if (!pdf_contains(bytes, "HairlineSans")) {
    warning(paste0("hairline: this R installation cannot reach the bundled font for PDF output, so the PDF uses a ",
                   "substitute font. Run hl_install_font() once (copies the font to your user font folder), or ",
                   "use formats = c(\"png\", \"svg\")."), call. = FALSE)
  }
}

#' Install the bundled font for PDF output
#'
#' Copies the bundled 'Hairline Sans' files into your user font folder so that
#' every PDF route (cairo, rsvg, Quartz) can embed it. Nothing is installed
#' unless you call this function.
#'
#' @param confirm Ask before copying (default in interactive sessions).
#' @return The installed file paths, invisibly.
#' @examples
#' if (interactive()) hl_install_font()
#' @export
hl_install_font <- function(confirm = interactive()) {
  folder <- switch(Sys.info()[["sysname"]],
                   Darwin = file.path(path.expand("~"), "Library", "Fonts"),
                   Windows = file.path(Sys.getenv("LOCALAPPDATA"), "Microsoft", "Windows", "Fonts"),
                   file.path(path.expand("~"), ".local", "share", "fonts"))
  if (confirm && !isTRUE(utils::askYesNo(sprintf("Copy the 'Hairline Sans' font files to %s?", folder)))) {
    return(invisible(character()))
  }
  dir.create(folder, recursive = TRUE, showWarnings = FALSE)
  sources <- vapply(names(hl_tokens()$font$files), font_file, character(1))
  targets <- file.path(normalizePath(folder), basename(sources))
  if (!all(file.copy(sources, targets, overwrite = TRUE))) {
    stop(sprintf("hairline: could not copy the font files to %s", folder), call. = FALSE)
  }
  message(sprintf("Installed 'Hairline Sans' (%d files) in %s", length(targets), folder))
  invisible(unname(targets))
}
