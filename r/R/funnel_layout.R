# Funnel plot axes and the entry point funnel_drawing().

funnel_axis_shapes <- function(spec, box, area, scale, style) {
  neutral <- style$neutral
  spacing <- hl_tokens()$spacing
  size <- style$sizes$label
  pad <- spacing$y_labels_plot * style$base
  breaks <- as.numeric(unlist(spec$y_axis$breaks))
  labels <- unlist(spec$y_axis$labels)
  shapes <- lapply(seq_along(breaks), function(index) {
    c(shape_text(area[1] - pad, baseline_for(scale$y(breaks[index]), style, "label"), labels[index], "label",
                 neutral$muted, "right"), part = "y_label")
  })
  for (value in breaks[breaks > 0]) {
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(area[1], scale$y(value)),
                                                                       c(area[3], scale$y(value))),
                                         color = neutral$grid, width = style$grid)
  }
  tick <- area[4] + spacing$x_tick_pad * size + style$cap_height * size
  x_breaks <- as.numeric(unlist(spec$x_axis$breaks))
  x_labels <- unlist(spec$x_axis$labels)
  for (index in seq_along(x_breaks)) {
    position <- scale$x(if (isTRUE(spec$ratio)) log(x_breaks[index]) else x_breaks[index])
    align <- c("left", "right", "center")[match(edge_hjust((position - area[1]) / (area[3] - area[1])), c(0, 1, 0.5))]
    shapes[[length(shapes) + 1]] <- c(shape_text(position, tick, x_labels[index], "label", neutral$muted, align),
                                      part = "x_label")
  }
  shapes[[length(shapes) + 1]] <- shape_text(area[3], tick + line_height(style, "label") + spacing$x_title * style$base,
                                             spec$x_title, "label", neutral$muted, "right")
  title_baseline <- area[2] - hl_tokens()$funnel$title_gap * style$base - style$descender * size
  shapes[[length(shapes) + 1]] <- shape_text(box[1], title_baseline, spec$y_title, "label", neutral$muted)
  shapes
}

funnel_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$funnel
  neutral <- style$neutral
  area <- funnel_area(spec, box, measure, style)
  scale <- funnel_scales(spec, area)
  deepest <- spec$y_axis$high
  pooled <- spec$pooled
  region <- rbind(c(scale$x(pooled), scale$y(0)), c(scale$x(pooled + rules$z * deepest), scale$y(deepest)),
                  c(scale$x(pooled - rules$z * deepest), scale$y(deepest)))
  shapes <- c(list(list(kind = "polygon", points = region, fill = neutral$band, role = "funnel")),
              funnel_axis_shapes(spec, box, area, scale, style))
  if (!is.null(spec$null)) {
    shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(scale$x(spec$null), area[2]),
                                                                       c(scale$x(spec$null), area[4])),
                                         color = neutral$muted, width = style$leader_width, part = "null")
  }
  shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(scale$x(pooled), area[2]),
                                                                     c(scale$x(pooled), area[4])),
                                       color = neutral$faint, width = style$leader_width,
                                       dash = hl_tokens()$forest$pooled_dash, part = "pooled")
  shapes[[length(shapes) + 1]] <- list(kind = "line", points = rbind(c(area[1], area[4]), c(area[3], area[4])),
                                       color = neutral$axis, width = style$axis_width)
  radius <- rules$point_radius * style$base
  angles <- 2 * pi * (0:23) / 24
  for (point in spec$points) {
    point <- as.numeric(unlist(point))
    shapes[[length(shapes) + 1]] <- list(kind = "polygon", role = "study", fill = spec$color,
                                         alpha = rules$point_opacity,
                                         points = cbind(scale$x(point[1]) + radius * cos(angles),
                                                        scale$y(point[2]) + radius * sin(angles)))
  }
  shapes
}

#' Funnel plot
#'
#' Effect against standard error (running down from 0) with pseudo 95 %
#' limits around the pooled estimate, a dashed pooled line and a solid null
#' line; the pooled estimate and Egger's test become the key numbers.
#'
#' @param data A data frame.
#' @param estimate,se Columns: effect and its standard error (on the log scale for ratios).
#' @param title,subtitle,caption Frame texts; the title defaults to the axis.
#' @param ratio Effects are ratios (log axis, null at 1).
#' @param pooled Pooled estimate; inverse-variance weighted when `NULL`.
#' @param x_title Axis title; defaults to the effect column.
#' @return A ggplot with the hairline frame.
#' @export
hl_funnel <- function(data, estimate, se, title = NULL, subtitle = NULL, caption = NULL, ratio = TRUE, pooled = NULL,
                      x_title = NULL) {
  spec <- funnel_spec(data, estimate, se, ratio, pooled, x_title)
  value <- if (ratio) exp(spec$pooled) else spec$pooled
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste("Funnel plot of", tolower(spec$x_title)), subtitle = subtitle,
                  caption = caption, x = NULL, y = NULL) + theme_hairline(axes = FALSE) +
    hl_panel_header(name = "Pooled", stats = c(Estimate = hl_format_number(value, 2), Egger = format_p(spec$egger)))
  plot@meta$hairline_drawing <- function(box, measure, style) funnel_drawing(spec, box, measure, style)
  plot
}
