# Register the bundled font with systemfonts (used by ragg and svglite) and resolve requested families.

font_file <- function(key) {
  path <- system.file("fonts", hl_tokens()$font$files[[key]], package = "hairline")
  if (!nzchar(path)) {
    stop(sprintf("hairline: bundled font file for weight %s missing; reinstall the package", key), call. = FALSE)
  }
  path
}

register_bundled_fonts <- function() {
  if (isTRUE(hairline_state$fonts_registered)) return(invisible(TRUE))
  family <- hl_tokens()$font$family
  systemfonts::register_font(family, plain = font_file("400"), bold = font_file("600"),
                             italic = font_file("400i"), bolditalic = font_file("600i"))
  systemfonts::register_font(paste(family, "Medium"), plain = font_file("500"), bold = font_file("600"),
                             italic = font_file("500i"), bolditalic = font_file("600i"))
  hairline_state$fonts_registered <- TRUE
  invisible(TRUE)
}

font_available <- function(family) {
  family %in% c(systemfonts::system_fonts()$family, systemfonts::registry_fonts()$family)
}

resolve_family <- function(requested) {
  register_bundled_fonts()
  bundled <- hl_tokens()$font$family
  if (is.null(requested) || identical(requested, bundled) || font_available(requested)) {
    return(requested %||% bundled)
  }
  if (!requested %in% hairline_state$warned_fonts) {
    hairline_state$warned_fonts <- c(hairline_state$warned_fonts, requested)
    warning(sprintf("hairline: font '%s' is not installed; using '%s'", requested, bundled), call. = FALSE)
  }
  bundled
}

# The base pdf() and postscript() devices (the default of Rscript and R CMD check) draw only the fonts in their own
# databases and fail on any other family. There hairline's families are drawn as Helvetica, said once per session.
alias_base_device_fonts <- function(family) {
  device <- names(grDevices::dev.cur())
  if (!device %in% c("pdf", "postscript")) return(invisible(FALSE))
  database <- if (device == "pdf") grDevices::pdfFonts else grDevices::postscriptFonts
  missing <- setdiff(c(family, paste(family, "Medium")), names(database()))
  if (length(missing) == 0) return(invisible(FALSE))
  do.call(database, stats::setNames(rep(list(database()$Helvetica), length(missing)), missing))
  if (!isTRUE(hairline_state$base_device_warned)) {
    hairline_state$base_device_warned <- TRUE
    warning(sprintf(paste0("hairline: the %s() device cannot draw '%s', so its text is drawn in Helvetica and may ",
                           "sit slightly off; hl_save() or a ragg device draws the real font"), device, family),
            call. = FALSE)
  }
  invisible(TRUE)
}
