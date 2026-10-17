helper_cases <- function() read_fixture("chart_helpers.json")

test_that("label spreading matches the shared fixture", {
  for (case in helper_cases()$labels) {
    result <- spread_labels(as.numeric(unlist(case$positions)), case$height, case$low, case$high)
    expect_equal(result, as.numeric(unlist(case$result)), tolerance = 1e-9,
                 info = paste(unlist(case$positions), collapse = ","))
  }
})

test_that("tints match the shared fixture", {
  for (case in helper_cases()$tints) {
    expect_equal(tints(case$color, case$count), as_colors(case$result), info = paste(case$color, case$count))
  }
})

test_that("folding into Other matches the shared fixture", {
  for (case in helper_cases()$fold) {
    result <- fold_other(as.character(unlist(case$labels)), as.numeric(unlist(case$values)), case$keep)
    expect_equal(result$labels, as.character(unlist(case$result[[1]])))
    expect_equal(result$values, as.numeric(unlist(case$result[[2]])))
  }
})
