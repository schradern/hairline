# R code is ASCII with \u escapes, as portable packages need: every string is then marked UTF-8 and keeps its
# characters in any locale, where a literal en dash would be re-read as native bytes outside UTF-8.

test_that("the package's R code is ASCII", {
  folder <- test_path("..", "..", "R")
  skip_if_not(dir.exists(folder), "package sources are not next to the tests")
  offending <- unlist(lapply(list.files(folder, "\\.R$", full.names = TRUE), function(path) {
    lines <- readLines(path, encoding = "UTF-8", warn = FALSE)
    code <- !grepl("^\\s*#", lines)
    found <- which(code & grepl("[^\\x01-\\x7f]", lines, perl = TRUE))
    if (length(found)) paste0(basename(path), ":", found) else character()
  }))
  expect_equal(offending, character())
})

