# Brand layers and export-type overrides, mirroring the Python package.

brand_outputs <- c("screen", "pdf", "html", "docx")

is_mapping <- function(value) is.list(value) && !is.null(names(value)) && all(nzchar(names(value)))

# The shape of each section hairline reads, one rule in both packages: a mapping names its values; a list may be
# written as its single value (yaml reads `[harbor]` and `harbor` alike).
brand_mappings <- c(meta = "its details (name: ...)", color = "colour roles to colours",
                    color.palette = "colour names to hex values", typography = "its parts (fonts, base, headings)",
                    defaults = "tools to their settings", defaults.hairline = "settings to values",
                    defaults.hairline.colors = "entity names to palette names or hex values",
                    defaults.hairline.groups = "group names to their members",
                    defaults.hairline.sizes = "text roles to sizes in pt",
                    defaults.hairline.outputs = "export types to their settings")
brand_lists <- c("typography.fonts", "defaults.hairline.categorical")

# An empty mapping or list (`{}`, `[]`) holds nothing, which every section may.
is_brand_mapping <- function(value) is_mapping(value) || (is.list(value) && !length(value))

brand_shown <- function(value) if (is.list(value)) "a list" else brand_value(value)

check_brand_shapes <- function(content, label) {
  for (key in names(brand_mappings)) {
    value <- brand_get(content, key)
    if (!is.null(value) && !is_brand_mapping(value)) {
      brand_fail(label, key, sprintf("must map %s; got %s", brand_mappings[[key]], brand_shown(value)))
    }
  }
  for (key in brand_lists) {
    if (is_mapping(brand_get(content, key))) brand_fail(label, key, "must list its entries; got a mapping")
  }
  fonts <- brand_get(content, "typography.fonts")
  for (index in seq_along(fonts)) {
    if (!is_mapping(fonts[[index]])) {
      brand_fail(label, sprintf("typography.fonts[%d]", index - 1),
                 sprintf("must be a mapping with family and source; got %s", brand_shown(fonts[[index]])))
    }
  }
}

# `layer` over `base`: mappings merge key by key, everything else (sequences included) is replaced.
merge_brand <- function(base, layer) {
  for (key in names(layer)) {
    base[key] <- list(if (is_mapping(layer[[key]]) && is_mapping(base[[key]])) merge_brand(base[[key]], layer[[key]])
                      else layer[[key]])
  }
  base
}

check_brand_output <- function(output) {
  if (!is.null(output) && !output %in% brand_outputs) {
    stop(sprintf("hairline: output '%s' must be one of %s", output, paste(brand_outputs, collapse = ", ")),
         call. = FALSE)
  }
}

read_brand_layers <- function(paths, output) {
  check_brand_output(output)
  layers <- lapply(paths, read_brand_yaml)
  label <- paste(basename(paths), collapse = " + ")
  with_fonts <- which(vapply(layers, function(layer) !is.null(brand_get(layer, "typography.fonts")), logical(1)))
  font_dir <- dirname(paths[if (length(with_fonts)) max(with_fonts) else length(paths)])
  content <- list()
  for (layer in layers) content <- merge_brand(content, layer)
  check_brand_shapes(content, label)
  outputs <- brand_get(content, "defaults.hairline.outputs") %||% list()
  for (name in names(outputs)) {
    key <- paste0("defaults.hairline.outputs.", name)
    if (!name %in% brand_outputs) {
      brand_fail(label, key, sprintf("must be one of %s", paste(brand_outputs, collapse = ", ")))
    }
    if (!is.null(outputs[[name]]) && !is_brand_mapping(outputs[[name]])) {
      brand_fail(label, key, sprintf("must be a mapping of settings; got %s", brand_shown(outputs[[name]])))
    }
  }
  if (!is.null(output) && length(outputs[[output]])) {
    content <- merge_brand(content, list(defaults = list(hairline = outputs[[output]])))
    check_brand_shapes(content, label)
  }
  list(content = content, label = label, font_dir = font_dir, path = paths[length(paths)], layers = layers,
       paths = normalizePath(paths), output = output)
}

entity_pair_failures <- function(colors) {
  limits <- hl_tokens()$checks
  failures <- character()
  if (length(colors) < 2) return(failures)
  for (pair in utils::combn(seq_along(colors), 2, simplify = FALSE)) {
    one <- colors[[pair[1]]]
    two <- colors[[pair[2]]]
    vision <- min(delta_e(one, two, "protan"), delta_e(one, two, "deutan"))
    normal <- delta_e(one, two)
    names <- paste(names(colors)[pair], collapse = " / ")
    if (vision < limits$cvd_floor) {
      failures <- c(failures, sprintf("%s: colour-vision \u0394E %.1f is below %s", names, vision, limits$cvd_floor))
    } else if (normal < limits$normal_floor) {
      failures <- c(failures, sprintf("%s: normal-vision \u0394E %.1f is below %s", names, normal, limits$normal_floor))
    }
  }
  failures
}

checked_entities <- function(colors, mode, label) {
  failures <- entity_pair_failures(colors)
  if (!length(failures)) return(list(colors = colors, failures = failures))
  if (mode == "readable") {
    adapted <- stats::setNames(suppressWarnings(adapt_readable(unname(colors), pairs = "all")), names(colors))
    return(list(colors = adapted, failures = entity_pair_failures(adapted)))
  }
  warning(sprintf("hairline: %s: pinned colours are hard to tell apart: %s", label, paste(failures, collapse = "; ")),
          call. = FALSE)
  list(colors = colors, failures = failures)
}

grouped_entities <- function(colors, groups, label) {
  for (group in names(groups)) {
    key <- paste0("defaults.hairline.groups.", group)
    if (!group %in% names(colors)) {
      brand_fail(label, key, sprintf("group '%s' needs a colour in defaults.hairline.colors", group))
    }
    members <- as.character(unlist(groups[[group]]))
    if (!length(members)) brand_fail(label, key, "must list the group's members")
    shades <- tints(colors[[group]], length(members))
    for (index in seq_along(members)) {
      if (!members[index] %in% names(colors)) colors[[members[index]]] <- shades[index]
    }
  }
  colors
}

# Which brand layer set a value, mirroring the Python package's brand_origins: its 1-based number, with the export
# type when an `outputs` override set it (that override applies last, so it is looked for first).
brand_has_path <- function(layer, keys) {
  node <- layer
  for (key in keys) {
    if (!is.list(node) || !key %in% names(node)) return(FALSE)
    node <- node[[key]]
  }
  TRUE
}

brand_origin <- function(layers, output, keys) {
  if (!is.null(output) && identical(keys[1:2], c("defaults", "hairline"))) {
    override <- c("defaults", "hairline", "outputs", output, keys[-(1:2)])
    for (index in rev(seq_along(layers))) {
      if (brand_has_path(layers[[index]], override)) return(sprintf("%d, %s", index, output))
    }
  }
  for (index in rev(seq_along(layers))) if (brand_has_path(layers[[index]], keys)) return(as.character(index))
  ""
}

# A palette name comes from `color.palette`; a hex entry from `categorical`, else primary/secondary/tertiary.
brand_slot_origins <- function(layers, output, names, palette) {
  vapply(names, function(name) {
    if (name %in% names(palette)) return(brand_origin(layers, output, c("color", "palette", name)))
    candidates <- c(brand_origin(layers, output, c("defaults", "hairline", "categorical")),
                    vapply(c("primary", "secondary", "tertiary"), function(role) {
                      brand_origin(layers, output, c("color", role))
                    }, character(1)))
    c(candidates[nzchar(candidates)], "")[1]
  }, character(1), USE.NAMES = FALSE)
}

# A pinned colour comes from `colors`; a group member's tint from the group in `groups` that lists it.
brand_entity_origins <- function(layers, output, entities, groups) {
  vapply(entities, function(name) {
    origin <- brand_origin(layers, output, c("defaults", "hairline", "colors", name))
    group <- Filter(function(group) name %in% unlist(groups[[group]]), names(groups %||% list()))
    if (!nzchar(origin) && length(group)) origin <- brand_origin(layers, output, c("defaults", "hairline", "groups",
                                                                                   group[1]))
    origin
  }, character(1))
}
