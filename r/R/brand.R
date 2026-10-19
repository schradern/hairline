# Read `_brand.yml` (the brand.yml format) and map it onto hairline settings.

brand_fail <- function(path, key, message) {
  stop(sprintf("hairline: %s: %s: %s", basename(path), key, message), call. = FALSE)
}

brand_get <- function(content, dotted) {
  value <- content
  for (key in strsplit(dotted, ".", fixed = TRUE)[[1]]) {
    if (!is.list(value) || is.null(value[[key]])) return(NULL)
    value <- value[[key]]
  }
  value
}

read_brand_yaml <- function(path) {
  if (!file.exists(path)) stop(sprintf("hairline: brand file %s does not exist", path), call. = FALSE)
  content <- tryCatch(yaml::read_yaml(path), error = function(error) {
    line <- regmatches(conditionMessage(error), regexpr("line [0-9]+", conditionMessage(error)))
    stop(sprintf("hairline: %s: %s: %s", basename(path), if (length(line)) line else "unknown position",
                 conditionMessage(error)), call. = FALSE)
  })
  if (is.null(content)) content <- list()
  if (!is.list(content) || is.null(names(content)) && length(content) > 0) {
    stop(sprintf("hairline: %s: the top level must be a mapping of sections", basename(path)), call. = FALSE)
  }
  content
}

is_hex <- function(value) is.character(value) && length(value) == 1 && grepl("^#[0-9a-fA-F]{6}$", value)

brand_palette <- function(content, path) {
  palette <- brand_get(content, "color.palette") %||% list()
  for (name in names(palette)) {
    if (!is_hex(palette[[name]])) {
      brand_fail(path, paste0("color.palette.", name), sprintf("'%s' is not a 6-digit hex colour", palette[[name]]))
    }
  }
  lapply(palette, tolower)
}

brand_color <- function(value, key, palette, path) {
  if (is.character(value) && length(value) == 1 && value %in% names(palette)) return(palette[[value]])
  if (is_hex(value)) return(tolower(value))
  brand_fail(path, key, sprintf("'%s' is not in color.palette and not a 6-digit hex colour", value))
}

brand_categorical <- function(content, palette, path) {
  entries <- brand_get(content, "defaults.hairline.categorical")
  if (is.null(entries)) {
    entries <- Filter(Negate(is.null), lapply(c("primary", "secondary", "tertiary"),
                                              function(role) brand_get(content, paste0("color.", role))))
  }
  names_out <- character()
  colors <- character()
  for (index in seq_along(entries)) {
    entry <- entries[[index]]
    key <- sprintf("defaults.hairline.categorical[%d]", index - 1)
    if (is.character(entry) && !startsWith(entry, "#") && !entry %in% names(palette)) {
      brand_fail(path, key, sprintf("'%s' is not in color.palette", entry))
    }
    colors <- c(colors, brand_color(entry, key, palette, path))
    names_out <- c(names_out, if (entry %in% names(palette)) entry else colors[length(colors)])
  }
  list(names = names_out, colors = colors)
}

brand_neutral <- function(content, palette, path) {
  neutral <- list()
  for (pair in list(c("foreground", "ink"), c("background", "surface"))) {
    value <- brand_get(content, paste0("color.", pair[1]))
    if (!is.null(value)) neutral[[pair[2]]] <- brand_color(value, paste0("color.", pair[1]), palette, path)
  }
  for (key in c("muted", "faint", "grid", "axis", "band")) {
    value <- brand_get(content, paste0("defaults.hairline.", key))
    if (!is.null(value)) neutral[[key]] <- brand_color(value, paste0("defaults.hairline.", key), palette, path)
  }
  neutral
}

warn_exact_brand <- function(name, labels, colors) {
  report <- hl_check_palette(colors)
  problems <- c(report$failures, vapply(report$light_slots, function(slot) {
    sprintf("%s (%s) is below 3:1 on white; it gets heavier lines and darker point fills", labels[slot], colors[slot])
  }, character(1)))
  if (length(problems)) {
    warning(sprintf("hairline: brand '%s' (adapt: exact): %s", name, paste(problems, collapse = "; ")), call. = FALSE)
  }
}

register_brand_fonts <- function(content, path, font_dir = dirname(path)) {
  fonts <- brand_get(content, "typography.fonts") %||% list()
  for (index in seq_along(fonts)) {
    entry <- fonts[[index]]
    source <- entry$source %||% "system"
    if (identical(source, "file")) {
      files <- vapply(entry$files, function(file) if (is.list(file)) file$path else file, character(1))
      paths <- normalizePath(file.path(font_dir, files), mustWork = FALSE)
      missing <- paths[!file.exists(paths)]
      if (length(missing)) brand_fail(path, sprintf("typography.fonts[%d].files", index - 1),
                                      sprintf("font file %s not found", missing[1]))
      register_font_family(entry$family, plain = paths[1])
    } else if (identical(source, "google")) {
      family <- entry$family %||% ""
      warning(sprintf(paste0("hairline: %s: typography.fonts[%d]: '%s' comes from Google Fonts, which hairline does ",
                             "not download; install it (https://fonts.google.com/specimen/%s) or put its files next ",
                             "to the brand file with source: file"), basename(path), index - 1, family,
                      gsub(" ", "+", family, fixed = TRUE)), call. = FALSE)
    }
  }
}

brand_entities <- function(content, palette, categorical, used, path) {
  mapping <- brand_get(content, "defaults.hairline.colors") %||% list()
  resolved <- character()
  for (entity in names(mapping)) {
    value <- mapping[[entity]]
    key <- paste0("defaults.hairline.colors.", entity)
    if (is.character(value) && value %in% categorical) {
      resolved[[entity]] <- used[match(value, categorical)]
    } else if (is.character(value) && (value %in% names(palette) || is_hex(value))) {
      resolved[[entity]] <- brand_color(value, key, palette, path)
    } else {
      brand_fail(path, key, sprintf("'%s' is not in color.palette and not a 6-digit hex colour", value))
    }
  }
  resolved
}

#' Read a brand file
#'
#' Parses a `_brand.yml` file in the brand.yml format. Errors name the file,
#' the key path and the offending value.
#'
#' @param path Path to `_brand.yml`, or several paths: layers from institution to document, later layers
#'   overriding earlier ones.
#' @param output Export type whose overrides apply: `"screen"`, `"pdf"`, `"html"` or `"docx"`.
#' @return A list with `name`, `path`, `names`, `colors_given`, `colors_used`, `adapt`, `font`,
#'   `heading_font`, `heading_weight`, `neutral`, `base_size`, `sizes`, `locale`, `entity_colors`,
#'   `entity_failures`, `output`, `sequential_hue`, `diverging_hues`, `layers` (the file paths), `slot_origins`
#'   and `entity_origins` (the layer that set each colour).
#' @examples
#' path <- file.path(tempdir(), "_brand.yml")
#' writeLines(c("meta:", "  name: Example Hospital", "color:", "  palette:",
#'              "    harbor: \"#0b3d6e\"", "    poppy: \"#f2545b\"", "defaults:", "  hairline:",
#'              "    categorical: [harbor, poppy]"), path)
#' brand <- hl_load_brand(path, output = "pdf")
#' brand$name
#' @export
hl_load_brand <- function(path, output = NULL) {
  source <- read_brand_layers(path, output)
  content <- source$content
  path <- source$label
  palette <- brand_palette(content, path)
  categorical <- brand_categorical(content, palette, path)
  adapt <- brand_get(content, "defaults.hairline.adapt") %||% "readable"
  if (!adapt %in% c("exact", "readable")) {
    brand_fail(path, "defaults.hairline.adapt", sprintf("'%s' must be 'exact' or 'readable'", adapt))
  }
  name <- brand_get(content, "meta.name")
  if (adapt == "exact" && length(categorical$colors)) warn_exact_brand(name, categorical$names, categorical$colors)
  register_brand_fonts(content, path, source$font_dir)
  locale <- brand_get(content, "defaults.hairline.locale")
  if (!is.null(locale) && !locale %in% names(hl_tokens()$locales)) {
    known <- paste(names(hl_tokens()$locales), collapse = ", ")
    brand_fail(path, "defaults.hairline.locale", sprintf("'%s' must be one of %s", locale, known))
  }
  used <- if (adapt == "readable" && length(categorical$colors)) adapt_readable(categorical$colors) else
    categorical$colors
  entities <- checked_entities(brand_entities(content, palette, categorical$names, used, path), adapt, path)
  groups <- brand_get(content, "defaults.hairline.groups") %||% list()
  entity_colors <- grouped_entities(entities$colors, groups, path)
  hues <- brand_ramp_hues(content, palette, path)
  list(name = name, path = normalizePath(source$path), names = categorical$names, colors_given = categorical$colors,
       colors_used = used, adapt = adapt, font = brand_get(content, "typography.base.family"),
       heading_font = brand_get(content, "typography.headings.family"),
       heading_weight = brand_get(content, "typography.headings.weight"),
       neutral = brand_neutral(content, palette, path), base_size = brand_get(content, "defaults.hairline.base_size"),
       sizes = brand_get(content, "defaults.hairline.sizes") %||% list(), locale = locale,
       entity_colors = entity_colors, entity_failures = entities$failures, output = output,
       sequential_hue = hues$sequential, diverging_hues = hues$diverging, layers = source$paths,
       slot_origins = brand_slot_origins(source$layers, output, categorical$names, palette),
       entity_origins = brand_entity_origins(source$layers, output, names(entity_colors), groups))
}

#' Find a brand file
#'
#' Looks for `_brand.yml` from `start` upwards and stops at the project root
#' (a folder containing `.git`, `_quarto.yml`, `pyproject.toml` or `DESCRIPTION`).
#'
#' @param start Folder to start from.
#' @return The path, or `NULL`.
#' @examples
#' path <- file.path(tempdir(), "_brand.yml")
#' writeLines(c("meta:", "  name: Example Hospital", "color:", "  palette:",
#'              "    harbor: \"#0b3d6e\"", "    poppy: \"#f2545b\"", "defaults:", "  hairline:",
#'              "    categorical: [harbor, poppy]"), path)
#' hl_find_brand(tempdir())
#' @export
hl_find_brand <- function(start = getwd()) {
  folder <- normalizePath(start, mustWork = FALSE)
  repeat {
    candidate <- file.path(folder, "_brand.yml")
    if (file.exists(candidate)) return(candidate)
    if (any(file.exists(file.path(folder, c(".git", "_quarto.yml", "pyproject.toml", "DESCRIPTION"))))) return(NULL)
    parent <- dirname(folder)
    if (identical(parent, folder)) return(NULL)
    folder <- parent
  }
}

#' Brand report
#'
#' @param brand A brand from [hl_load_brand()], or `NULL` for the active one.
#' @return A character string: the layers by number with their paths, then per slot the name, colour as
#'   given and as used, light slot and the layer that set it, the checks, and the pinned or grouped colours with
#'   their layers.
#' @examples
#' path <- file.path(tempdir(), "_brand.yml")
#' writeLines(c("meta:", "  name: Example Hospital", "color:", "  palette:",
#'              "    harbor: \"#0b3d6e\"", "    poppy: \"#f2545b\"", "defaults:", "  hairline:",
#'              "    categorical: [harbor, poppy]"), path)
#' hl_brand_report(hl_load_brand(path))
#' @export
hl_brand_report <- function(brand = NULL) {
  brand <- brand %||% hairline_state$brand
  if (is.null(brand)) return("No brand is active.")
  report <- if (length(brand$colors_used)) hl_check_palette(brand$colors_used) else NULL
  layers <- brand$layers %||% brand$path
  rows <- c(sprintf("Brand '%s' (adapt: %s)", brand$name, brand$adapt),
            sprintf("layer %d: %s", seq_along(layers), layers), "slot  name        given    used     light  layer")
  for (slot in seq_along(brand$colors_used)) {
    light <- if (!is.null(report) && slot %in% report$light_slots) "yes" else ""
    origin <- if (slot <= length(brand$slot_origins)) brand$slot_origins[slot] else ""
    row <- sprintf("%-5d %-11s %s  %s  %-5s  %s", slot, brand$names[slot], brand$colors_given[slot],
                   brand$colors_used[slot], light, origin)
    rows <- c(rows, sub("\\s+$", "", row))
  }
  checks <- if (is.null(report)) "checks: no colours" else if (report$passed) "checks: passed" else
    paste("checks:", paste(report$failures, collapse = "; "))
  entities <- brand$entity_colors %||% character()
  origins <- if (is.null(brand$entity_origins)) rep("", length(entities)) else brand$entity_origins[names(entities)]
  tags <- ifelse(!is.na(origins) & nzchar(origins), sprintf(" (layer %s)", origins), "")
  entity_rows <- c(sprintf("entity %s: %s%s", names(entities), unlist(entities), tags),
                   sprintf("entity check: %s", brand$entity_failures %||% character()))
  paste(c(rows, checks, if (length(entities)) entity_rows), collapse = "\n")
}

resolve_brand <- function(brand, output = NULL) {
  if (isFALSE(brand)) return(NULL)
  if (is.list(brand)) return(brand)
  path <- if (is.null(brand)) hl_find_brand() else brand
  if (is.null(path)) return(NULL)
  loaded <- hl_load_brand(path, output)
  if (is.null(brand) && !normalizePath(path) %in% hairline_state$announced) {
    hairline_state$announced <- c(hairline_state$announced, normalizePath(path))
    message(sprintf("Using brand '%s' from %s", loaded$name, path))
  }
  loaded
}

brand_layer <- function(settings, brand) {
  hairline_state$brand <- brand
  if (is.null(brand)) return(settings)
  settings$brand_name <- brand$name
  settings$neutral <- utils::modifyList(settings$neutral, brand$neutral)
  settings$sizes <- validated_sizes(brand$sizes)
  if (length(brand$colors_used)) {
    label <- sprintf("brand '%s'", brand$name)
    settings[c("palette", "palette_name", "palette_label")] <- list(brand$colors_used, "brand", label)
  }
  if (!is.null(brand$font)) settings$font <- resolve_family(brand$font)
  if (!is.null(brand$base_size)) {
    settings[c("base_size", "base_size_explicit")] <- list(as.numeric(brand$base_size), TRUE)
  }
  if (!is.null(brand$locale)) settings$locale <- brand$locale
  settings$ramps <- brand_ramps(brand)
  settings
}
