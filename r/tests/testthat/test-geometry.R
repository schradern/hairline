flatten_numbers <- function(value) {
  if (is.null(value)) return(numeric())
  if (is.list(value)) value <- unlist(lapply(value, flatten_numbers), use.names = FALSE)
  if (is.null(value)) numeric() else as.numeric(value)
}

test_that("frame geometry reproduces every Python fixture case", {
  metrics <- font_metrics()
  for (case in read_fixture("frame.json")) {
    layout <- compute_frame(case$input, metrics)
    for (key in names(case$layout)) {
      expect_equal(flatten_numbers(layout[[key]]), flatten_numbers(case$layout[[key]]), tolerance = 1e-6,
                   label = key)
    }
  }
})

test_that("too small figures are reported", {
  spec <- list(width_pt = 482, height_pt = 120, base_size = 9, panel_rows = 4,
               sizes = list(title = 13.5, subtitle = 9, panel = 9, label = 8.1, caption = 7.65))
  expect_error(compute_frame(spec, font_metrics()), "too small")
})
