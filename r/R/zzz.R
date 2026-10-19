.onLoad <- function(libname, pkgname) {
  register_frame_methods()
  point_fontconfig_at_bundled_font()
  # Inside a host document (HAIRLINE_HOST_CONTEXT set), start from the document's context.
  if (!is.null(host_context())) hl_use()
}

.onUnload <- function(libpath) {
  restore_fontconfig()
}
