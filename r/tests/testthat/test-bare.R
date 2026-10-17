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

line_plot <- function() {
  ggplot2::ggplot(data.frame(x = c(0, 10), y = c(0, 1)), ggplot2::aes(x, y)) + ggplot2::geom_line() +
    ggplot2::labs(title = "T", caption = "Note.") + theme_hairline()
}

with_table <- function(plot, rows, heading = NULL) {
  plot@meta$hairline_table <- list(heading = heading, rows = rows)
  plot
}

test_that("the table band sits between axis and caption", {
  hl_use(brand = FALSE)
  rows <- list(list(label = "Group A", colour = "#2474cf", x = c(0, 5, 10), text = c("40", "31", "12")),
               list(label = "Group B", colour = "#e8a628", x = c(0, 5, 10), text = c("38", "20", "6")))
  plain <- hl_layout_report(line_plot())
  report <- hl_layout_report(with_table(line_plot(), rows, "Number at risk"))
  panel <- report$panels[[1]]
  expect_length(report$table_baselines, 3)
  expect_lt(panel[2] + panel[4], report$table_baselines[1])
  expect_lt(report$table_baselines[3], report$caption_baselines[1])
  expect_lt(report$panels[[1]][4], plain$panels[[1]][4])
})

test_that("table values align with their x position", {
  hl_use(brand = FALSE)
  rows <- list(list(label = "Group A", colour = "#2474cf", x = c(0, 10), text = c("40", "12")))
  report <- hl_layout_report(with_table(line_plot(), rows))
  box <- report$plot_boxes[[1]]
  expect_equal(report$table_value_xs, c(box[1], box[1] + box[3]), tolerance = 0.1)
})
