square <- function() data.frame(x = c(0, 1), y = c(0, 1))

bare_plot <- function(extra = NULL) {
  ggplot2::ggplot(square(), ggplot2::aes(x, y)) + ggplot2::geom_point() + ggplot2::labs(title = "T") + extra +
    theme_hairline(axes = FALSE)
}

test_that("a bare panel has no ticks, grid or baseline", {
  hl_use(brand = FALSE)
  frame <- ggplot2::ggplotGrob(bare_plot())
  expect_true(frame$parts$bare)
  expect_s3_class(ggplot2::ggplot_build(bare_plot())@plot@theme$panel.grid, "ggplot2::element_blank")
})

test_that("a bare panel reserves no tick label space", {
  hl_use(brand = FALSE)
  regular <- hl_layout_report(ggplot2::ggplot(square(), ggplot2::aes(x, y)) + ggplot2::geom_point() +
                                ggplot2::labs(title = "T") + theme_hairline())
  bare <- hl_layout_report(bare_plot())
  expect_equal(bare$panels[[1]][1], bare$left)
  expect_gt(bare$panels[[1]][4], regular$panels[[1]][4])
  expect_equal(bare$bare_panels, 0L)
})

test_that("a fixed-aspect bare panel is centred", {
  hl_use(brand = FALSE)
  report <- hl_layout_report(bare_plot(ggplot2::coord_fixed()))
  box <- report$plot_boxes[[1]]
  panel <- report$panels[[1]]
  expect_equal(box[3], box[4], tolerance = 0.5)
  expect_equal(box[1] + box[3] / 2, panel[1] + panel[3] / 2, tolerance = 0.5)
  expect_equal(box[2], panel[2], tolerance = 0.5)
})
