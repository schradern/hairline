donut_fixture <- function() read_fixture("donut.json")

fake_measure <- function(style) function(text, role, weight = NULL) 0.5 * style$sizes[[role]] * nchar(text)

as_spec <- function(spec) {
  spec$rings <- lapply(spec$rings, function(ring) lapply(ring, function(segment) {
    segment$value <- as.numeric(segment$value)
    segment
  }))
  spec
}

flat_shapes <- function(shapes) {
  unlist(lapply(shapes, function(shape) {
    if (shape$kind == "text") c(shape$x, shape$y) else as.numeric(t(shape_points(shape)))
  }))
}

test_that("donut geometry matches the shared fixture", {
  fixture <- donut_fixture()
  for (case in fixture$cases) {
    shapes <- donut_drawing(as_spec(case$spec), as.numeric(unlist(case$box)), fake_measure(fixture$style),
                            fixture$style)
    expect_equal(length(shapes), length(case$shapes), info = case$spec$labels)
    expect_equal(vapply(shapes, `[[`, character(1), "kind"), vapply(case$shapes, `[[`, character(1), "kind"))
    expect_equal(flat_shapes(shapes), flat_shapes(case$shapes), tolerance = 1e-6, info = case$spec$labels)
    texts <- Filter(function(shape) shape$kind == "text", case$shapes)
    expect_equal(vapply(Filter(function(shape) shape$kind == "text", shapes), `[[`, character(1), "text"),
                 vapply(texts, `[[`, character(1), "text"))
  }
})

test_that("donut rings match the shared fixture", {
  for (case in donut_fixture()$cases) {
    hl_use(brand = FALSE)
    data <- as.data.frame(lapply(case$data, unlist), stringsAsFactors = FALSE)
    rings <- donut_rings(data, case$label, "n", if (is.null(case$levels)) NULL else unlist(case$levels))
    expected <- case$spec$rings
    expect_equal(length(rings), length(expected))
    for (ring in seq_along(rings)) {
      for (field in c("name", "share_text", "color")) {
        expect_equal(vapply(rings[[ring]], `[[`, character(1), field),
                     vapply(expected[[ring]], `[[`, character(1), field), info = field)
      }
      expect_equal(vapply(rings[[ring]], `[[`, numeric(1), "share"),
                   vapply(expected[[ring]], function(segment) as.numeric(segment$share), numeric(1)))
    }
  }
})

test_that("more than seven slices fold into Other", {
  hl_use(brand = FALSE)
  rings <- donut_rings(data.frame(name = letters[1:10], value = 10:1), "name", "value")
  expect_equal(vapply(rings[[1]], `[[`, character(1), "name"), c(letters[1:6], "Other"))
})

test_that("four levels and negative values are refused", {
  hl_use(brand = FALSE)
  expect_error(donut_rings(data.frame(a = "x", b = "y", c = "z", d = "w", n = 1), NULL, "n", c("a", "b", "c", "d")),
               "at most 3 levels")
  expect_error(donut_rings(data.frame(name = c("Home", "Rehab"), value = c(3, -1)), "name", "value"),
               "'Rehab' has a negative value")
})

test_that("the donut plot reports its labels", {
  hl_use(brand = FALSE)
  data <- data.frame(destination = c("Home", "Rehab", "Ward", "Care home", "Died"), patients = c(412, 168, 97, 54, 23))
  report <- hl_layout_report(hl_donut(data, "destination", "patients", title = "Discharge", total_label = "patients"))
  expect_equal(report$bare_panels, 0L)
  expect_length(report$drawing_texts, 2 * 5 + 2)
})

test_that("order sets the top ring sequence", {
  data <- data.frame(destination = c("Home", "Rehab", "Ward", "Care home", "Died"), patients = c(412, 168, 97, 54, 23))
  rings <- donut_rings(data, "destination", "patients", order = c("Died", "Home"))
  expect_equal(vapply(rings[[1]], `[[`, character(1), "name"), c("Died", "Home", "Rehab", "Ward", "Care home"))
})

test_that("a folded Other slice uses the scheme's context grey", {
  hl_use(brand = FALSE, scheme = "dark")
  on.exit(hl_use(brand = FALSE))
  data <- data.frame(unit = LETTERS[1:9], patients = 9:1)
  ring <- donut_rings(data, "unit", "patients")[[1]]
  other <- ring[[length(ring)]]
  expect_equal(other$name, "Other")
  expect_equal(other$color, hl_tokens()$focus$context_dark)
})
