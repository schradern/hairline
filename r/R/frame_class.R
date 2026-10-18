# theme_hairline(): a theme that also turns the plot into a hairline_plot, so that every route to a
# gtable (print, ggsave, knitr, ggplotGrob) passes through hl_gtable() and gets the full frame.

hairline_plot <- S7::new_class("hairline_plot", parent = ggplot2::class_ggplot, package = "hairline",
                               constructor = function(plot) {
                                 object <- S7::new_object(plot)
                                 class(object) <- unique(c("hairline::hairline_plot", class(plot)))
                                 object
                               })

hairline_theme <- S7::new_class("hairline_theme", package = "hairline",
                                properties = list(elements = S7::class_any, settings = S7::class_any,
                                                  axes = S7::class_logical))

#' hairline theme and frame
#'
#' Adds hairline's theme and frame to a ggplot: title, subtitle, legend row,
#' panel headers and caption on one left edge, with the spacing scale applied
#' wherever the plot is printed or saved.
#'
#' @param base_size Body text size in pt; `NULL` uses the active setting.
#' @param font Font family; `NULL` uses the active setting.
#' @param axes `FALSE` draws panels without axes, ticks, grid or baseline (donut, Sankey and the like);
#'   with `coord_fixed()` the plot area keeps its shape, centred in the panel.
#' @return An object to add to a ggplot with `+`.
#' @export
theme_hairline <- function(base_size = NULL, font = NULL, axes = TRUE) {
  settings <- hl_settings()
  if (!is.null(base_size)) settings[c("base_size", "base_size_explicit")] <- list(as.numeric(base_size), TRUE)
  if (!is.null(font)) settings$font <- resolve_family(font)
  theme_object(settings, axes)
}

theme_object <- function(settings, axes = TRUE) {
  elements <- theme_hairline_elements(settings)
  if (!isTRUE(axes)) {
    blank <- ggplot2::element_blank()
    elements <- elements + ggplot2::theme(axis.text = blank, axis.ticks = blank, axis.line = blank, panel.grid = blank)
  }
  hairline_theme(elements = elements, settings = settings, axes = isTRUE(axes))
}

update_hairline_plot <- function(object, plot, ...) {
  plot <- ggplot2::update_ggplot(object@elements, plot, ...)
  # The frame draws one baseline under every panel; ggplot's own x axis line would double it.
  plot <- ggplot2::update_ggplot(ggplot2::theme(axis.line.x = ggplot2::element_blank()), plot, ...)
  if (!S7::S7_inherits(plot, hairline_plot)) plot <- hairline_plot(plot)
  plot@meta$hairline_settings <- object@settings
  plot@meta$hairline_bare <- !object@axes
  plot
}

build_hairline_plot <- function(plot, ...) {
  built <- NextMethod()
  extra <- c(default_position_scales(plot, built), entity_scales(plot, built))
  if (length(extra) > 0) {
    for (scale in extra) plot <- suppressMessages(plot + scale)
    return(ggplot2::ggplot_build(plot))
  }
  built <- apply_light_slots(apply_highlight(built))
  class(built) <- c("hairline_built", class(built))
  built
}

called_from_package <- function(package) {
  for (frame in rev(seq_len(sys.nframe()))) {
    environment <- environment(sys.function(frame))
    if (!is.null(environment) && identical(environmentName(topenv(environment)), package)) return(TRUE)
  }
  FALSE
}

gtable_hairline_built <- function(data) {
  table <- NextMethod()
  # patchwork aligns the gtables of several plots itself; there each plot keeps the theme but not the frame.
  if (called_from_package("patchwork")) return(table)
  trace <- getOption("hairline.trace_frame")
  if (is.function(trace)) trace()
  host_hand_off(data@plot)
  hl_gtable(table, data)
}

register_frame_methods <- function() {
  signature <- list(hairline_theme, ggplot2::class_ggplot)
  suppressMessages(S7::`method<-`(ggplot2::update_ggplot, signature, value = update_hairline_plot))
  signature <- list(hairline_header, ggplot2::class_ggplot)
  suppressMessages(S7::`method<-`(ggplot2::update_ggplot, signature, value = add_hairline_header))
  signature <- list(hairline_highlight, ggplot2::class_ggplot)
  suppressMessages(S7::`method<-`(ggplot2::update_ggplot, signature, value = add_hairline_highlight))
  signature <- list(hairline_legend, ggplot2::class_ggplot)
  suppressMessages(S7::`method<-`(ggplot2::update_ggplot, signature, value = add_hairline_legend))
  signature <- list(hairline_reference, ggplot2::class_ggplot)
  suppressMessages(S7::`method<-`(ggplot2::update_ggplot, signature, value = add_hairline_reference))
  registerS3method("ggplot_build", "hairline::hairline_plot", build_hairline_plot,
                   envir = asNamespace("ggplot2"))
  registerS3method("ggplot_gtable", "hairline_built", gtable_hairline_built, envir = asNamespace("ggplot2"))
}
