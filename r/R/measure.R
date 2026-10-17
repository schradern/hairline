# Measure and wrap text in pt with systemfonts (72 dpi, so 1 px = 1 pt).

style_family <- function(style) {
  if (style$weight == 500 && font_available(paste(style$family, "Medium"))) paste(style$family, "Medium") else
    style$family
}

text_width_pt <- function(text, style) {
  if (!nzchar(text)) return(0)
  systemfonts::string_width(text, family = style_family(style), size = style$size, res = 72,
                            weight = if (style$weight >= 600) "bold" else "normal")
}

wrap_text <- function(text, style, max_width) {
  if (is.null(text) || !nzchar(text)) return(character())
  lines <- character()
  for (paragraph in strsplit(text, "\n", fixed = TRUE)[[1]]) {
    current <- ""
    for (word in strsplit(trimws(paragraph), "\\s+")[[1]]) {
      candidate <- if (nzchar(current)) paste(current, word) else word
      if (nzchar(current) && text_width_pt(candidate, style) > max_width) {
        lines <- c(lines, current)
        current <- word
      } else {
        current <- candidate
      }
    }
    lines <- c(lines, current)
  }
  lines
}

role_style <- function(settings, role, weight = NULL, colour = NULL) {
  definition <- hl_tokens()$type$roles[[role]]
  list(family = settings$font, size = role_size(settings, role), weight = weight %||% definition$weight,
       colour = colour %||% settings$neutral[[definition$color]])
}

text_grob_pt <- function(text, x, baseline, style, height, align = "left") {
  grid::textGrob(text, x = grid::unit(x, "pt"), y = grid::unit(height - baseline, "pt"),
                 hjust = if (align == "right") 1 else 0, vjust = 0,
                 gp = grid::gpar(fontfamily = style_family(style), fontsize = style$size, col = style$colour,
                                 fontface = if (style$weight >= 600) "bold" else "plain"))
}
