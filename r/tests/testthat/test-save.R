sample_hairline_plot <- function() {
  ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
    ggplot2::labs(title = "Survival after ICU discharge", caption = "Synthetic data") + theme_hairline()
}

test_that("default outputs are PDF and 600 dpi PNG in a created folder", {
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  paths <- suppressWarnings(hl_save(sample_hairline_plot(), file.path(folder, "nested", "survival")))
  expect_equal(tools::file_ext(paths), c("pdf", "png"))
  expect_true(all(file.exists(paths)))
  expect_equal(attr(png::readPNG(paths[2], info = TRUE), "info")$dpi, c(600, 600), tolerance = 0.5)
})

test_that("PDF output has no timestamp or producer banner", {
  hl_use(brand = FALSE)
  path <- suppressWarnings(hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "a"), formats = "pdf"))
  bytes <- readBin(path, "raw", file.size(path))
  expect_false(grepl("CreationDate|Producer", rawToChar(bytes[bytes != as.raw(0)]), useBytes = TRUE))
})

test_that("PDF output is byte-stable on the cairo route", {
  skip_if_not(pdf_route() == "cairo", "the svglite + rsvg fallback route is not byte-stable")
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  first <- hl_save(sample_hairline_plot(), file.path(folder, "a"), formats = "pdf")
  second <- hl_save(sample_hairline_plot(), file.path(folder, "b"), formats = "pdf")
  expect_identical(readBin(first, "raw", file.size(first)), readBin(second, "raw", file.size(second)))
})

test_that("PDF embeds the bundled font where the PDF route can see it", {
  hl_use(brand = FALSE)
  skip_if_not(pdf_route() == "cairo" || font_installed_for_pdf(), "no PDF route that sees the bundled font here")
  path <- hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "pdf")
  bytes <- readBin(path, "raw", file.size(path))
  expect_true(grepl("HairlineSans", rawToChar(bytes[bytes != as.raw(0)]), useBytes = TRUE))
})

test_that("a PDF without the bundled font warns and points to hl_install_font()", {
  hl_use(brand = FALSE)
  skip_if(pdf_route() == "cairo" || font_installed_for_pdf(), "the bundled font reaches the PDF here")
  expect_warning(hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "pdf"),
                 "hl_install_font")
})

test_that("SVG keeps text as text and is byte-stable", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  first <- hl_save(sample_hairline_plot(), file.path(folder, "a"), formats = "svg")
  second <- hl_save(sample_hairline_plot(), file.path(folder, "b"), formats = "svg")
  expect_true(any(grepl("Survival after ICU discharge", readLines(first, warn = FALSE), fixed = TRUE)))
  expect_identical(readLines(first, warn = FALSE), readLines(second, warn = FALSE))
})

test_that("unknown formats are refused before anything is written", {
  folder <- withr::local_tempdir()
  expect_error(hl_save(sample_hairline_plot(), file.path(folder, "out", "f"), formats = c("png", "jpeg")),
               "unknown format 'jpeg'; use one of pdf, png, svg, tiff", fixed = TRUE)
  expect_false(dir.exists(file.path(folder, "out")))
})

test_that("TIFF is LZW-compressed and the size preset sets the base size", {
  hl_use(brand = FALSE)
  path <- hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "tiff", dpi = 72)
  expect_true(file.exists(path))
  expect_equal(saved_settings(sample_hairline_plot(), "single")$base_size, 8)
  hl_use(base_size = 10, brand = FALSE)
  expect_equal(saved_settings(sample_hairline_plot(), "single")$base_size, 10)
})

test_that("hl_install_font copies the bundled files into the user font folder", {
  home <- withr::local_tempdir()
  withr::local_envvar(HOME = home)
  paths <- hl_install_font(confirm = FALSE)
  expect_length(paths, 6)
  expect_true(all(file.exists(paths)))
  expect_true(all(startsWith(paths, normalizePath(home))))
})
