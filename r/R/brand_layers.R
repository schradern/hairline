# Brand layers and export-type overrides, mirroring the Python package.

brand_outputs <- c("screen", "pdf", "html", "docx")

is_mapping <- function(value) is.list(value) && !is.null(names(value)) && all(nzchar(names(value)))

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
  outputs <- brand_get(content, "defaults.hairline.outputs") %||% list()
  for (name in names(outputs)) {
    if (!name %in% brand_outputs) {
      brand_fail(label, paste0("defaults.hairline.outputs.", name),
                 sprintf("must be one of %s", paste(brand_outputs, collapse = ", ")))
    }
  }
  if (!is.null(output) && !is.null(outputs[[output]])) {
    content <- merge_brand(content, list(defaults = list(hairline = outputs[[output]])))
  }
  list(content = content, label = label, font_dir = font_dir, path = paths[length(paths)])
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
