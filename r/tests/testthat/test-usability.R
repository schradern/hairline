discharges <- function() {
  data.frame(route = rep(c("Home", "Rehabilitation", "Care home"), c(5, 3, 2)),
             detail = rep(c("Alone", "With support", "Inpatient", "Care home"), c(3, 2, 3, 2)))
}

stays <- function() {
  set.seed(2)
  data.frame(unit = rep(c("Surgical", "Medical", "Neuro"), each = 30),
             length_of_stay = round(c(rgamma(30, 2, 0.5), rgamma(30, 3, 0.5), rgamma(30, 4, 0.4)), 1))
}

trial <- function() {
  set.seed(4)
  data.frame(arm = rep(c("A", "B"), each = 40), months = round(rexp(80, 1 / 12), 1),
             died = as.integer(runif(80) < 0.7))
}

drawn_texts <- function(plot) {
  hl_use(brand = FALSE)
  style <- drawing_style(hl_settings())
  shapes <- plot@meta$hairline_drawing(c(0, 0, 400, 220), measure_for(hl_settings()), style)
  vapply(Filter(function(shape) shape$kind == "text", shapes), `[[`, character(1), "text")
}

test_that("titles come from the columns", {
  hl_use(brand = FALSE)
  expect_equal(hl_raincloud(stays(), "unit", "length_of_stay")@labels$title, "Length of stay by unit")
  expect_equal(hl_donut(discharges(), "route")@labels$title, "Count by route")
  expect_equal(hl_partition(discharges(), c("route", "detail"))@labels$title, "Count by route and detail")
  expect_equal(hl_kaplan_meier(trial(), "months", "died", by = "arm")@labels$title, "Survival by arm")
})

test_that("raw rows are counted", {
  texts <- drawn_texts(hl_donut(discharges(), "route"))
  expect_true(all(c("50%", "10") %in% texts))
})

test_that("Kaplan-Meier adds the log-rank test, also from a formula", {
  hl_use(brand = FALSE)
  plot <- hl_kaplan_meier(trial(), survival::Surv(months, died) ~ arm)
  expect_match(plot@meta$hairline_headers[[1]]$stats[["Log-rank"]], "^p ")
  expect_equal(plot@labels$title, "Survival by arm")
})

test_that("the raincloud computes its comparisons, also from a formula", {
  hl_use(brand = FALSE)
  plot <- hl_raincloud(stays(), length_of_stay ~ unit, comparisons = "all")
  geoms <- vapply(plot@layers, function(layer) class(layer$geom)[1], character(1))
  labels <- unlist(lapply(plot@layers[geoms == "GeomText"], function(layer) layer$aes_params$label))
  expect_length(labels, 3)
  expect_true(all(startsWith(labels, "p ")))
})

test_that("the forest plot reads a fitted model", {
  hl_use(brand = FALSE)
  set.seed(7)
  data <- data.frame(age = rnorm(200, 60, 10), sepsis = rbinom(200, 1, 0.4))
  data$died <- rbinom(200, 1, plogis(-4 + 0.05 * data$age + 0.8 * data$sepsis))
  model <- stats::glm(died ~ age + sepsis, family = stats::binomial, data = data)
  plot <- hl_forest(model)
  texts <- drawn_texts(plot)
  expect_true(all(c("age", "sepsis") %in% texts))
  expect_false("(Intercept)" %in% texts)
  expect_equal(plot@labels$title, "Effects by term")
})
