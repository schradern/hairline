# ggplot2 theme elements derived from hairline settings and tokens.

pt_to_mm <- function(value) value / ggplot2::.pt

# ggplot draws a linewidth of 1 as .pt line-width units of 1/96 inch, so a width in pt needs 96/72 more.
pt_to_linewidth <- function(value) pt_to_mm(value / 0.75)

text_element <- function(settings, role, colour = NULL, face = NULL, ...) {
  definition <- hl_tokens()$type$roles[[role]]
  ggplot2::element_text(family = settings$font, size = role_size(settings, role),
                        colour = colour %||% settings$neutral[[definition$color]],
                        face = face %||% if (definition$weight >= 600) "bold" else "plain", ...)
}

frame_text_elements <- function(settings) {
  spacing <- hl_tokens()$spacing
  base <- settings$base_size
  ggplot2::theme(
    plot.title = text_element(settings, "title", hjust = 0,
                              margin = ggplot2::margin(b = spacing$title_subtitle * base)),
    plot.subtitle = text_element(settings, "subtitle", hjust = 0,
                                 margin = ggplot2::margin(b = spacing$header_legend * base)),
    plot.caption = text_element(settings, "caption", hjust = 0,
                                margin = ggplot2::margin(t = spacing$content_caption * base)),
    plot.title.position = "plot", plot.caption.position = "plot",
    strip.text = text_element(settings, "panel", hjust = 0, margin = ggplot2::margin(b = spacing$panel_header * base)),
    axis.text = text_element(settings, "label", colour = settings$neutral$faint),
    axis.text.y = text_element(settings, "label", colour = settings$neutral$faint, hjust = 1,
                               margin = ggplot2::margin(r = 0)),
    axis.text.x = text_element(settings, "label", colour = settings$neutral$faint, margin = ggplot2::margin(t = 0)),
    axis.text.y.left = text_element(settings, "label", colour = settings$neutral$faint, hjust = 1,
                                    margin = ggplot2::margin(0, 0, 0, 0)),
    axis.text.x.bottom = text_element(settings, "label", colour = settings$neutral$faint,
                                      margin = ggplot2::margin(0, 0, 0, 0)),
    axis.title = text_element(settings, "label"),
    axis.title.y = text_element(settings, "label", angle = 0, vjust = 1, hjust = 0),
    axis.title.x = text_element(settings, "label", hjust = 1),
    legend.text = text_element(settings, "label")
  )
}

frame_line_elements <- function(settings) {
  lines <- hl_tokens()$lines
  base <- settings$base_size
  ggplot2::theme(
    panel.grid.major.y = ggplot2::element_line(colour = settings$neutral$grid,
                                               linewidth = pt_to_linewidth(lines$grid * base)),
    panel.grid.major.x = ggplot2::element_blank(), panel.grid.minor = ggplot2::element_blank(),
    axis.line.x = ggplot2::element_line(colour = settings$neutral$axis, linewidth = pt_to_linewidth(lines$axis * base)),
    axis.line.y = ggplot2::element_blank(), axis.ticks = ggplot2::element_blank(),
    axis.ticks.x = ggplot2::element_blank(), axis.ticks.y = ggplot2::element_blank(),
    axis.ticks.length = grid::unit(0, "pt"), panel.border = ggplot2::element_blank(),
    panel.background = ggplot2::element_blank(), strip.background = ggplot2::element_blank()
  )
}

frame_layout_elements <- function(settings) {
  spacing <- hl_tokens()$spacing
  base <- settings$base_size
  surface <- if (identical(settings$background, "transparent")) NA else settings$background
  ggplot2::theme(
    legend.position = "top", legend.justification = "left", legend.location = "plot",
    legend.title = ggplot2::element_blank(), legend.margin = ggplot2::margin(0, 0, 0, 0),
    legend.box.spacing = grid::unit(spacing$legend_content * base, "pt"),
    legend.key = ggplot2::element_blank(), legend.background = ggplot2::element_blank(),
    panel.spacing.y = grid::unit(spacing$panel_rows * base, "pt"),
    panel.spacing.x = grid::unit(spacing$panel_columns * base, "pt"),
    plot.margin = ggplot2::margin(spacing$margin * base, spacing$margin * base, spacing$margin * base,
                                  spacing$margin * base),
    plot.background = ggplot2::element_rect(fill = surface, colour = NA)
  )
}

frame_palette_elements <- function(settings) {
  lines <- hl_tokens()$lines
  ggplot2::theme(
    palette.colour.discrete = function(n) hl_palette(n = n), palette.fill.discrete = function(n) hl_palette(n = n),
    palette.colour.continuous = hl_ramp("blues"), palette.fill.continuous = hl_ramp("blues"),
    geom = ggplot2::element_geom(ink = settings$neutral$ink, accent = settings$palette[1], paper = "#ffffff",
                                 linewidth = pt_to_linewidth(lines$data * settings$base_size),
                                 pointsize = pt_to_mm(2 * lines$point_radius * settings$base_size / 0.75),
                                 family = settings$font)
  )
}

theme_hairline_elements <- function(settings = hl_settings()) {
  ggplot2::theme_minimal(base_size = settings$base_size, base_family = settings$font) +
    frame_text_elements(settings) + frame_line_elements(settings) + frame_layout_elements(settings) +
    frame_palette_elements(settings)
}
