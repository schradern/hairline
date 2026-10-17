test_that("number fixtures match the Python reference", {
  for (case in read_fixture("numbers.json")) {
    formatter <- if (case$kind == "number") hl_format_number else hl_format_percent
    expect_equal(formatter(case$value, case$digits, case$locale), case$result,
                 label = paste(case$kind, case$value, case$digits, case$locale))
  }
  expect_equal(hl_format_interval(0.58, 0.41, 0.82, 2, "de"), "0,58 [0,41; 0,82]")
  expect_error(hl_format_number(1, 0, "fr"), "unknown locale 'fr'")
})

test_that("break fixtures match the Python reference", {
  for (case in read_fixture("breaks.json")) {
    expect_equal(nice_breaks(case$low, case$high), unlist(case$breaks), tolerance = 1e-12,
                 label = paste(case$low, case$high))
  }
  expect_error(nice_breaks(5, 1), "low 5 is above high 1")
})
