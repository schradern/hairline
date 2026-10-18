# Active settings and hl_use(), the one call that sets the style.

default_settings <- function() {
  tokens <- hl_tokens()
  name <- tokens$default_palette
  list(font = tokens$font$family, base_size = tokens$type$base_size, sizes = list(),
       palette = unname(tokens$palettes[[name]]), palette_name = name, palette_label = sprintf("palette '%s'", name),
       locale = tokens$default_locale, background = "#ffffff", neutral = tokens$neutral, brand_name = NULL,
       base_size_explicit = FALSE)
}

#' Active hairline settings
#' @return The settings list set by the last [hl_use()], or the defaults.
#' @export
hl_settings <- function() hairline_state$settings %||% default_settings()

role_size <- function(settings, role) {
  settings$sizes[[role]] %||% (hl_tokens()$type$roles[[role]]$factor * settings$base_size)
}

validated_sizes <- function(sizes) {
  roles <- names(hl_tokens()$type$roles)
  unknown <- setdiff(names(sizes), roles)
  if (length(unknown) > 0) {
    stop(sprintf("hairline: unknown text role '%s' in sizes; use one of %s", unknown[1],
                 paste(sort(roles), collapse = ", ")), call. = FALSE)
  }
  as.list(sizes %||% list())
}

palette_fields <- function(palette) {
  if (is.null(palette)) return(list())
  colors <- hl_palette(palette)
  named <- is.character(palette) && length(palette) == 1 && !startsWith(palette, "#")
  list(palette = colors, palette_name = if (named) palette else "custom",
       palette_label = if (named) sprintf("palette '%s'", palette) else "custom palette")
}

#' Set hairline's style for this session
#'
#' Precedence: these arguments > the brand (`brand =` path, or a `_brand.yml`
#' found from the working directory up to the project root; `brand = FALSE`
#' disables the lookup) > hairline's defaults.
#'
#' @param font Font family; falls back to the bundled 'Hairline Sans' with a warning when missing.
#' @param base_size Body text size in pt; every other size derives from it.
#' @param sizes Named list of role sizes in pt (`title`, `subtitle`, `panel`, `label`, `caption`).
#' @param palette Palette name or vector of hex colours.
#' @param locale `"en"` or `"de"`.
#' @param background `"#ffffff"`-style colour or `"transparent"`.
#' @param brand Path to a `_brand.yml`, several paths as layers (institution first), `NULL` to look one up,
#'   or `FALSE`.
#' @param colors Named vector of entity colours, e.g. `c("Unit B" = "#e8a628")`; see [hl_color()].
#' @param output Export type whose brand overrides apply: `"screen"`, `"pdf"`, `"html"` or `"docx"`.
#' @return The active settings, invisibly.
#' @export
hl_use <- function(font = NULL, base_size = NULL, sizes = NULL, palette = NULL, locale = NULL,
                   background = NULL, brand = NULL, colors = NULL, output = NULL) {
  hairline_state$use_arguments <- list(font = font, base_size = base_size, sizes = sizes, palette = palette,
                                       locale = locale, background = background, brand = brand, colors = colors,
                                       output = output)
  context <- host_context()
  if (!is.null(context)) {
    locale <- locale %||% context$locale
    base_size <- base_size %||% context$base_size
    if (is.null(brand) && !is.null(context$brand)) brand <- context$brand
    output <- output %||% context$output
    font <- font %||% context$design$font
  }
  register_bundled_fonts()
  if (!is.null(locale)) locale_symbols(locale)
  explicit <- validated_entity_colors(colors)
  resolved_brand <- resolve_brand(brand, output)
  settings <- brand_layer(default_settings(), resolved_brand)
  settings <- utils::modifyList(settings, palette_fields(palette))
  if (!is.null(font)) settings$font <- resolve_family(font)
  if (!is.null(sizes)) settings$sizes <- utils::modifyList(settings$sizes, validated_sizes(sizes))
  if (!is.null(base_size)) settings[c("base_size", "base_size_explicit")] <- list(as.numeric(base_size), TRUE)
  if (!is.null(locale)) settings$locale <- locale
  if (!is.null(background)) settings$background <- background
  hairline_state$settings <- settings
  brand_colors <- resolved_brand$entity_colors %||% character()
  configure_entities(c(brand_colors[setdiff(names(brand_colors), names(explicit))], explicit))
  ggplot2::theme_set(theme_hairline_elements(settings))
  invisible(settings)
}

# Apply the last hl_use() call again (its own arguments, the current host context under them): what a new host
# context calls. A session that never called hl_use() has nothing to re-apply.
hl_reapply <- function() {
  if (is.null(hairline_state$settings)) return(invisible())
  do.call(hl_use, hairline_state$use_arguments %||% list())
}
