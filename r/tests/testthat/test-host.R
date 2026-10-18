local_host_context <- function(folder, ..., envir = parent.frame()) {
  content <- utils::modifyList(list(version = 1, host = "editor", output = "pdf", width_mm = 150,
                                    figure_dir = file.path(folder, "f"), design = list(font = "Hairline Sans"),
                                    dpi = 144), list(...))
  path <- tempfile(tmpdir = folder, fileext = ".json")
  jsonlite::write_json(content, path, auto_unbox = TRUE)
  withr::local_envvar(c(HAIRLINE_HOST_CONTEXT = path), .local_envir = envir)
  withr::defer({
    hairline_state$host_path <- NULL
    hairline_state$host_context <- NULL
    hairline_state$handed_off <- NULL
  }, envir = envir)
  path
}

test_that("the host width is the default and a printed plot is handed off once with a manifest entry", {
  folder <- withr::local_tempdir()
  local_host_context(folder)
  hl_use(brand = FALSE)
  expect_equal(figure_size_mm("onehalf", NULL, NULL)[1], 150)
  expect_equal(figure_size_mm("onehalf", 80, NULL)[1], 80)
  plot <- ggplot2::ggplot(data.frame(x = 1:3, y = c(1, 3, 2)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Lactate by unit", subtitle = "Admissions 2025") + theme_hairline()
  path <- tempfile(fileext = ".png")
  ragg::agg_png(path, width = 8, height = 6, units = "in", res = 72)
  print(plot)
  print(plot)
  grDevices::dev.off()
  entries <- jsonlite::read_json(file.path(folder, "f", "hairline-figures.json"))
  expect_length(entries, 1)
  expect_setequal(names(entries[[1]]$files), c("pdf", "png"))
  expect_equal(entries[[1]]$width_mm, 150)
  expect_equal(entries[[1]]$alt, "Lactate by unit. Admissions 2025")
})

test_that("a bad host context warns once and hairline carries on", {
  folder <- withr::local_tempdir()
  path <- file.path(folder, "broken.json")
  writeLines("{not json", path)
  withr::local_envvar(c(HAIRLINE_HOST_CONTEXT = path))
  withr::defer({
    hairline_state$host_path <- NULL
    hairline_state$host_context <- NULL
  })
  expect_warning(expect_null(host_context()), "not valid JSON")
  expect_equal(figure_size_mm("onehalf", NULL, NULL)[1], 120)
})

test_that("explicit arguments win over the host context", {
  folder <- withr::local_tempdir()
  local_host_context(folder, output = "html", locale = "de")
  expect_equal(hl_use(brand = FALSE, locale = "en")$locale, "en")
  expect_equal(hl_use(brand = FALSE)$locale, "de")
  expect_equal(host_formats[[host_context()$output]], c("svg", "png"))
  hl_use(brand = FALSE, locale = "en")
})

test_that("a plot drawn again after the host empties its folder is handed off again", {
  folder <- withr::local_tempdir()
  local_host_context(folder)
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = 1:3, y = c(1, 3, 2)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "Lactate by unit") + theme_hairline()
  draw <- function() {
    ragg::agg_png(tempfile(fileext = ".png"), width = 8, height = 6, units = "in", res = 72)
    print(plot)
    grDevices::dev.off()
  }
  draw()
  unlink(list.files(file.path(folder, "f"), full.names = TRUE))
  draw()
  entries <- jsonlite::read_json(file.path(folder, "f", "hairline-figures.json"))
  expect_length(entries, 1)
  expect_true(all(file.exists(unlist(entries[[1]]$files))))
})

test_that("a new host context re-applies the style and keeps explicit arguments", {
  folder <- withr::local_tempdir()
  local_host_context(folder, locale = "de")
  hl_use(brand = FALSE)
  expect_equal(hairline_state$settings$locale, "de")
  local_host_context(folder, locale = "en")
  host_context()
  expect_equal(hairline_state$settings$locale, "en")
  hl_use(brand = FALSE, base_size = 11)
  local_host_context(folder, base_size = 8, locale = "de")
  host_context()
  expect_equal(hairline_state$settings$base_size, 11)
  expect_equal(hairline_state$settings$locale, "de")
  hl_use(brand = FALSE, locale = "en")
})
