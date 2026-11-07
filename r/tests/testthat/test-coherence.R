built_axis_colour <- function(plot, element) {
  ggplot2::ggplot_build(plot)@plot@theme[[element]]@colour
}

test_that("names are ink and numbers faint", {
  hl_use(brand = FALSE)
  neutral <- hl_settings()$neutral
  plot <- hl_bars(data.frame(unit = c("Medical", "Surgical"), n = c(3, 5)), "unit", "n", horizontal = TRUE)
  expect_equal(built_axis_colour(plot, "axis.text.y.left"), neutral$ink)
  expect_equal(built_axis_colour(plot, "axis.text.x.bottom"), neutral$faint)
  years <- hl_bars(data.frame(year = c("2024", "2025"), n = c(3, 5)), "year", "n", horizontal = FALSE)
  expect_equal(built_axis_colour(years, "axis.text.x.bottom"), neutral$faint)
})

test_that("a binned key starts at the left edge", {
  hl_use(brand = FALSE)
  plot <- hl_likert(data.frame(s = rep(c("A", "B"), each = 5), r = rep(1:5, 2)), "s", "r", levels = 1:5)
  legend <- interactive_targets(plot)$legend
  expect_equal(legend[[1]]$box[[1]], hl_layout_report(plot)$left, tolerance = 0.01)
})

test_that("interval headings follow the locale", {
  rates <- data.frame(unit = c("A", "B"), mortality = c(0.1, 0.2), low = c(0.05, 0.1), high = c(0.2, 0.3))
  hl_use(brand = FALSE)
  expect_equal(word("interval", name = "Mortality (%)"), "Mortality (%) [95% CI]")
  plot <- hl_dotplot(rates, "unit", "mortality", "low", "high", percent = TRUE, digits = 0)
  expect_s3_class(plot, "ggplot")
  hl_use(brand = FALSE, locale = "de")
  expect_equal(word("interval", name = "Mortality (%)"), "Mortality (%) [95 %-KI]")
  hl_use(brand = FALSE)
})

test_that("a ramp name colours ordered groups light to dark", {
  hl_use(brand = FALSE)
  colours <- colours_for(c("Low", "Medium", "High"), "blues")
  expect_equal(unname(colours), hl_ramp("blues", 5)[3:5])
  expect_error(colours_for("Low", "nope"), "unknown ramp")
})

test_that("levels by role shade in greys and arcs name their key", {
  hl_use(brand = FALSE)
  staff <- data.frame(start = c("2026-01-05 08:00", "2026-01-05 09:00"),
                      end = c("2026-01-05 12:00", "2026-01-05 15:00"), role = c("Doctors", "Nurses"))
  plot <- hl_levels(staff, "start", end = "end", by = "role")
  colours <- vapply(interactive_targets(plot)$series, `[[`, "", "color")
  expect_true(length(colours) > 0 && !any(tolower(colours) %in% tolower(hl_palette()[1:2])))
  moves <- data.frame(origin = c("ICU", "Ward"), destination = c("Ward", "Home"))
  expect_equal(arcs_spec(moves, "origin", "destination")$key_title, "Count")
  expect_equal(arcs_spec(moves, "origin", "destination", key_title = "Moves")$key_title, "Moves")
})
