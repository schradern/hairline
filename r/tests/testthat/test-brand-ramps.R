ramp_fixture <- function() read_fixture("brand_ramps.json")
example_brand_path <- function() test_path("..", "..", "..", "brands", "example", "_brand.yml")

test_that("the ramp rule matches the shared fixture and reproduces the token ramps", {
  fixture <- ramp_fixture()
  for (case in fixture$rule$sequential) {
    expect_equal(sequential_ramp(case$hue), unlist(case$colors))
  }
  for (case in fixture$rule$diverging) {
    hues <- as.numeric(unlist(case$hues))
    expect_equal(diverging_ramp(hues[1], hues[2]), unlist(case$colors))
  }
  definition <- hl_tokens()$ramp_definitions
  for (name in names(definition$sequential)) {
    expect_equal(sequential_ramp(definition$sequential[[name]]), unname(hl_tokens()$ramps[[name]]), info = name)
  }
  for (name in names(definition$diverging)) {
    hues <- definition$diverging[[name]]
    expect_equal(diverging_ramp(hues[1], hues[2]), unname(hl_tokens()$ramps[[name]]), info = name)
  }
})

test_that("a brand's ramps match Python's, from its first colours or named hues", {
  skip_if_not(file.exists(example_brand_path()), "the example brand is not next to the tests")
  fixture <- ramp_fixture()
  hl_use(brand = example_brand_path())
  on.exit(hl_use(brand = FALSE))
  expect_equal(lapply(hl_settings()$ramps, unname), lapply(fixture$example, unlist))
  path <- file.path(withr::local_tempdir(), "_brand.yml")
  writeLines(fixture$explicit_yaml, path)
  hl_use(brand = path)
  expect_equal(lapply(hl_settings()$ramps, unname), lapply(fixture$explicit, unlist))
})

test_that("the default ramp, scales and heatmap follow the brand", {
  skip_if_not(file.exists(example_brand_path()), "the example brand is not next to the tests")
  hl_use(brand = FALSE)
  on.exit(hl_use(brand = FALSE))
  expect_equal(hl_ramp(), hl_ramp("blues"))
  expect_error(hl_ramp("brand-sequential"), "unknown ramp 'brand-sequential'; available ramps: blues", fixed = TRUE)
  hl_use(brand = example_brand_path())
  expect_equal(hl_ramp(), hl_settings()$ramps[["brand-sequential"]])
  expect_equal(default_ramp("diverging"), "brand-diverging")
  expect_equal(hl_ramp("blues"), unname(hl_tokens()$ramps$blues))
  catalogue <- hl_palettes()
  rows <- catalogue[catalogue$name %in% c("brand-sequential", "brand-diverging"), ]
  expect_equal(rows$kind, c("sequential", "diverging"))
  expect_equal(rows$slots, c(7L, 13L))
})

test_that("a diverging brand entry needs two colours", {
  path <- file.path(withr::local_tempdir(), "_brand.yml")
  writeLines(c("color:", "  palette:", "    harbor: \"#0b3d6e\"", "defaults:", "  hairline:",
               "    diverging: [harbor]"), path)
  expect_error(hl_load_brand(path), "defaults.hairline.diverging: must list two colours", fixed = TRUE)
})

test_that("a Google font names the font and the fix, as in Python", {
  path <- file.path(withr::local_tempdir(), "_brand.yml")
  writeLines(c("typography:", "  fonts:", "    - family: Source Serif 4", "      source: google"), path)
  expect_warning(hl_load_brand(path), paste0("'Source Serif 4' comes from Google Fonts, which hairline does not ",
                                             "download; install it (https://fonts.google.com/specimen/Source+Serif+4) ",
                                             "or put its files next to the brand file with source: file"),
                 fixed = TRUE)
})
