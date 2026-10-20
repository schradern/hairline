# The CITATION file read directly, as citation("hairline") reads it from an installed package.
read_citation <- function() {
  utils::readCitationFile(system.file("CITATION", package = "hairline"),
                          meta = list(Version = as.character(utils::packageVersion("hairline")), Encoding = "UTF-8"))
}

test_that("the citation gives the same entry as the Python package", {
  entry <- unname(as.character(utils::toBibtex(read_citation())))
  expect_equal(entry[1], "@Manual{schrader2026hairline,")
  expect_true(sprintf("  note = {R package version %s},", utils::packageVersion("hairline")) %in% entry)
  expect_true("  doi = {10.5281/zenodo.23456212}," %in% entry)
  expect_match(format(read_citation(), style = "text"), "Schrader N \\(2026\\)")
})
