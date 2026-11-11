cases <- jsonlite::read_json(test_path("fixtures", "stress.json"), simplifyVector = FALSE)$cases

test_that("hl_check_layout finds text over text and marks outside their plot", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  plot <- ggplot2::ggplot(data.frame(x = c(0, 1), y = c(0, 1)), ggplot2::aes(x, y)) +
    ggplot2::geom_point(size = 6) + ggplot2::annotate("text", x = 0.5, y = 0.5, label = c("Overlap", "Overlap")) +
    ggplot2::labs(title = "Two labels on one spot") + theme_hairline() +
    ggplot2::scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    ggplot2::scale_y_continuous(limits = c(0, 1), expand = c(0, 0))
  rules <- unique(vapply(hl_check_layout(plot), `[[`, "", "rule"))
  expect_setequal(rules, c("text_overlap", "mark_outside"))
})

test_that("hard cases draw without collisions or are refused plainly", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  for (case in cases) {
    data <- as.data.frame(lapply(case$data, unlist), check.names = FALSE)
    arguments <- lapply(case$args, unlist)
    found <- tryCatch(hl_check_layout(do.call(paste0("hl_", case$chart), c(list(data), arguments)), size = case$size),
                      error = function(error) {
                        expect_match(conditionMessage(error), "hairline:.*(use a wider size|Shorten)")
                        list()
                      })
    expect_length(found, 0)
  }
})

test_that("counts tick at whole numbers and years keep their order", {
  hl_use(brand = FALSE)
  plot <- hl_bars(data.frame(year = c("2021", "2019", "2020"), count = c(1, 2, 3)), "year", "count")
  params <- ggplot2::ggplot_build(plot)@layout$panel_params[[1]]
  expect_equal(as.character(params$x$get_labels()), c("2019", "2020", "2021"))
  breaks <- stats::na.omit(params$y$breaks)
  expect_true(all(breaks == round(breaks)))
})

test_that("many named groups share one colour and long names wrap", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  groups <- paste("Group", 0:9, "with a long name")
  data <- data.frame(group = rep(groups, each = 5), value = 0:49)
  rows <- spread_spec(data, "group", "value")$rows
  expect_length(unique(vapply(rows, `[[`, "", "color")), 1)
  plot <- hl_raincloud(data[data$group %in% groups[1:4], ], "group", "value")
  expect_length(hl_check_layout(plot, size = "onehalf"), 0)
})
