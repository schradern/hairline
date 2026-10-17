sample_plot <- function() {
  ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() + ggplot2::labs(title = "Fuel use")
}

test_that("theme_hairline turns a ggplot into a hairline plot that survives further additions", {
  hl_use(brand = FALSE)
  plot <- sample_plot() + theme_hairline()
  expect_true(S7::S7_inherits(plot, hairline_plot))
  plot <- plot + ggplot2::geom_line() + ggplot2::labs(subtitle = "Synthetic")
  expect_true(S7::S7_inherits(plot, hairline_plot))
  expect_length(plot@layers, 2)
})

test_that("ggplotGrob, print and ggsave all go through the hairline frame", {
  hl_use(brand = FALSE)
  plot <- sample_plot() + theme_hairline()
  expect_true(isTRUE(attr(ggplot2::ggplotGrob(plot), "hairline_frame")))
  path <- withr::local_tempfile(fileext = ".png")
  ragg::agg_png(path, width = 400, height = 300)
  frame_seen <- FALSE
  withr::with_options(list(hairline.trace_frame = function() frame_seen <<- TRUE), print(plot))
  grDevices::dev.off()
  expect_true(frame_seen)
  frame_seen <- FALSE
  withr::with_options(list(hairline.trace_frame = function() frame_seen <<- TRUE),
                      ggplot2::ggsave(withr::local_tempfile(fileext = ".png"), plot, width = 4, height = 3, dpi = 72))
  expect_true(frame_seen)
})

test_that("plain ggplots are untouched", {
  expect_null(attr(ggplot2::ggplotGrob(sample_plot()), "hairline_frame"))
})
