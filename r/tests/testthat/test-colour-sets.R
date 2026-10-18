swatch_fixture <- function() read_fixture("swatches.json")
swatch_fake <- function(style) function(text, role, weight = NULL) 0.5 * style$sizes[[role]] * nchar(text)
swatch_flat <- function(items) unlist(lapply(items, function(shape) {
  if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
}))
swatch_field <- function(items, field) vapply(items, function(shape) as.character(shape[[field]] %||% ""), character(1))

test_that("swatch geometry matches the shared fixture", {
  fixture <- swatch_fixture()
  for (case in fixture$cases) {
    hl_use(brand = FALSE)
    rows <- swatch_rows(if (is.null(case$names)) NULL else unlist(case$names))
    expect_equal(vapply(rows, `[[`, character(1), "name"), vapply(case$rows, `[[`, character(1), "name"))
    shapes <- swatches_drawing(list(rows = rows), as.numeric(unlist(case$box)), swatch_fake(fixture$style),
                               fixture$style)
    expect_equal(swatch_flat(shapes), swatch_flat(case$shapes), tolerance = 1e-6)
    for (field in c("text", "tip", "series", "edge")) {
      expect_equal(swatch_field(shapes, field), swatch_field(case$shapes, field), info = field)
    }
  }
})

test_that("purpose sets are palettes by name", {
  expect_equal(hl_palette("pair"), c("#0a6ddd", "#de4642"))
  expect_equal(hl_palette("pair-violet"), c("#5152c1", "#ef852e"))
  expect_equal(hl_palette("ink", n = 3), c("#1b1e22", "#4a5057", "#767c84"))
  expect_equal(hl_palette("judgement"), c("#009775", "#e8a628", "#b93780"))
})

test_that("a purpose set can be the active palette", {
  hl_use(brand = FALSE, palette = "pair")
  on.exit(hl_use(brand = FALSE))
  expect_equal(hl_settings()$palette, c("#0a6ddd", "#de4642"))
  expect_error(hl_palette(n = 3), "palette 'pair' has 2 slots but 3 categories", fixed = TRUE)
})

test_that("a ramp is not a palette, and unknown names list the choices", {
  expect_error(hl_palette("blues"), "'blues' is a ramp, not a palette; use hl_ramp('blues')", fixed = TRUE)
  expect_error(hl_palette("sunset"), paste("available palettes: daylight, calm, deep, lagoon, citrus, bold, pair,",
                                           "pair-teal, pair-violet, ink, judgement"), fixed = TRUE)
})

test_that("the catalogue lists every colour set with its use, as in Python", {
  hl_use(brand = FALSE)
  table <- hl_palettes()
  expect_equal(names(table), c("name", "kind", "slots", "active", "use", "colors"))
  expect_equal(unique(table$kind), c("categorical", "purpose", "sequential", "diverging"))
  expect_equal(nrow(table), 18)
  daylight <- table[table$name == "daylight", ]
  expect_true(daylight$active)
  expect_equal(daylight$use, "vivid; the default")
  expect_equal(strsplit(daylight$colors, " ")[[1]], hl_palette("daylight"))
  expect_equal(hl_palettes("purpose")$name, c("pair", "pair-teal", "pair-violet", "ink", "judgement"))
  expect_error(hl_palettes("warm"), "unknown kind 'warm'; use one of categorical, purpose, sequential, diverging",
               fixed = TRUE)
})

test_that("a custom active palette leads the catalogue", {
  hl_use(brand = FALSE, palette = c("#0b3d6e", "#f2545b"))
  on.exit(hl_use(brand = FALSE))
  first <- hl_palettes()[1, ]
  expect_equal(c(first$name, first$kind, first$colors), c("custom", "categorical", "#0b3d6e #f2545b"))
  expect_true(first$active)
  expect_false(any(hl_palettes()$active[-1]))
})

test_that("swatches draw every set by default and name an unknown one", {
  hl_use(brand = FALSE)
  plot <- hl_swatches()
  expect_equal(plot@labels$title, "Colour sets")
  report <- hl_layout_report(plot)
  expect_gt(length(report$drawing_texts), 30)
  expect_error(hl_swatches("sunset"), "unknown colour set 'sunset'", fixed = TRUE)
})

test_that("a palette is not a ramp", {
  expect_error(hl_ramp("daylight"), "'daylight' is a palette, not a ramp; use hl_palette('daylight')", fixed = TRUE)
})
