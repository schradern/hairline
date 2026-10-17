read_fixture <- function(name) {
  jsonlite::read_json(testthat::test_path("fixtures", name), simplifyVector = FALSE)
}

as_colors <- function(values) vapply(values, identity, character(1))
