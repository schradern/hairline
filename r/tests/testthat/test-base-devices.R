# The base pdf() device, the default of Rscript and R CMD check, knows only the fonts in its own database.

test_that("a plot prints on the base pdf() device, in Helvetica, with one warning", {
  hl_use(brand = FALSE)
  hairline_state$base_device_warned <- NULL
  plot <- ggplot2::ggplot(datasets::mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
    ggplot2::labs(title = "Fuel use by weight") + theme_hairline()
  grDevices::pdf(withr::local_tempfile(fileext = ".pdf"))
  on.exit(grDevices::dev.off(), add = TRUE)
  expect_warning(print(plot), "pdf\\(\\) device .*Helvetica.*hl_save\\(\\)")
  expect_no_warning(print(plot))
  expect_true(hl_settings()$font %in% names(grDevices::pdfFonts()))
})
