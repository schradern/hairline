.onLoad <- function(libname, pkgname) {
  register_frame_methods()
  # Inside a host document (HAIRLINE_HOST_CONTEXT set), start from the document's context.
  if (!is.null(host_context())) hl_use()
}
