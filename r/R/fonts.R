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
  register_font_family(family, plain = font_file("400"), bold = font_file("600"),
                       italic = font_file("400i"), bolditalic = font_file("600i"))
  register_font_family(paste(family, "Medium"), plain = font_file("500"), bold = font_file("600"),
                       italic = font_file("500i"), bolditalic = font_file("600i"))
  hairline_state$fonts_registered <- TRUE
  invisible(TRUE)
}

# systemfonts refuses to register a family that is already a system font (installed, or seen through the bundled
# fontconfig on Linux); such a family is used as it is. Returns whether the family was registered.
register_font_family <- function(family, ...) {
  if (family %in% systemfonts::system_fonts()$family) return(invisible(FALSE))
  systemfonts::register_font(family, ...)
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

# The weight a browser takes from `available` for `requested` (CSS font matching): from 400 to 500 the requested
# weight up to 500, then lighter, then heavier; below 400 lighter first; above 500 heavier first. Weight 600 of a
# family with 400 and 700 is 700.
nearest_weight <- function(requested, available) {
  if (!length(available) || requested %in% available) return(requested)
  lighter <- sort(available[available < requested], decreasing = TRUE)
  heavier <- sort(available[available > requested])
  candidates <- if (requested >= 400 && requested <= 500) {
    c(heavier[heavier <= 500], lighter, heavier[heavier > 500])
  } else if (requested < 400) {
    c(lighter, heavier)
  } else {
    c(heavier, lighter)
  }
  candidates[1]
}

font_weight_levels <- c(thin = 100, ultralight = 200, light = 300, normal = 400, medium = 500, semibold = 600,
                        bold = 700, ultrabold = 800, heavy = 900)

# Weights of the upright faces of `family`, read once per family: the bundled family's font files, else the faces
# systemfonts knows (installed or registered).
family_weights <- function(family) {
  known <- hairline_state$family_weights %||% list()
  if (!is.null(known[[family]])) return(known[[family]])
  files <- names(hl_tokens()$font$files)
  weights <- if (identical(family, hl_tokens()$font$family)) {
    as.numeric(files[!grepl("i$", files)])
  } else {
    columns <- c("family", "weight", "italic")
    fonts <- rbind(as.data.frame(systemfonts::system_fonts())[columns],
                   as.data.frame(systemfonts::registry_fonts())[columns])
    upright <- fonts$weight[fonts$family == family & !fonts$italic]
    sort(unique(unname(font_weight_levels[as.character(upright[!is.na(upright)])])))
  }
  known[[family]] <- weights
  hairline_state$family_weights <- known
  weights
}

# The weight of the face `family` has for `requested`, so text is measured and drawn in a face that exists (a
# semibold title in Helvetica Neue is its bold), as the Python package resolves it.
face_weight <- function(family, requested) nearest_weight(requested, family_weights(family))

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
