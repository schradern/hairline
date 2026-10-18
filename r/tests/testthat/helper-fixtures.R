read_fixture <- function(name) {
  jsonlite::read_json(testthat::test_path("fixtures", name), simplifyVector = FALSE)
}

as_colors <- function(values) vapply(values, identity, character(1))

# Runs `expr` without the warning that this machine's PDF route cannot reach the bundled font (it depends on the
# installation, not on the code under test); every other warning still surfaces.
without_pdf_font_warning <- function(expr) {
  withCallingHandlers(expr, warning = function(warning) {
    if (grepl("hl_install_font", conditionMessage(warning), fixed = TRUE)) invokeRestart("muffleWarning")
  })
}
