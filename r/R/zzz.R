.onLoad <- function(libname, pkgname) {
  register_frame_methods()
  point_fontconfig_at_bundled_font()
  # Measured and drawn in the bundled font from the first plot, not only after hl_use().
  register_bundled_fonts()
  # Inside a host document (HAIRLINE_HOST_CONTEXT set), start from the document's context.
  # A style that cannot be applied (a broken brand file) is warned about instead of stopping the package from loading.
  if (!is.null(host_context())) {
    tryCatch(hl_use(), error = function(error) {
      warning(sprintf("hairline: the host context's style could not be applied (%s); using the defaults",
                      conditionMessage(error)), call. = FALSE)
    })
  }
}

.onUnload <- function(libpath) {
  restore_fontconfig()
}
