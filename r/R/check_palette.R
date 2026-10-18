# Palette checks: lightness band, chroma floor, colour-vision separation, normal vision, light slots.

pair_indices <- function(count, pairs = c("adjacent", "all")) {
  pairs <- match.arg(pairs)
  if (count < 2) return(list())
  if (pairs == "all") return(utils::combn(count, 2, simplify = FALSE))
  lapply(seq_len(count - 1), function(index) c(index, index + 1))
}

worst_cvd <- function(colors, indices) {
  if (length(indices) == 0) return(100)
  min(vapply(indices, function(pair) {
    min(delta_e(colors[pair[1]], colors[pair[2]], "protan"), delta_e(colors[pair[1]], colors[pair[2]], "deutan"))
  }, numeric(1)))
}

worst_normal <- function(colors, indices) {
  if (length(indices) == 0) return(100)
  min(vapply(indices, function(pair) delta_e(colors[pair[1]], colors[pair[2]]), numeric(1)))
}

band_failures <- function(colors, limits) {
  oklch <- lapply(colors, hex_to_oklch)
  failures <- character()
  for (index in seq_along(colors)) {
    values <- oklch[[index]]
    if (values[1] < limits$lightness[1] || values[1] > limits$lightness[2]) {
      failures <- c(failures, sprintf("lightness: slot %d %s has L %.3f, outside %s-%s", index, colors[index],
                                      values[1], limits$lightness[1], limits$lightness[2]))
    }
    if (values[2] < limits$chroma_floor) {
      failures <- c(failures, sprintf("chroma: slot %d %s has C %.3f, below %s", index, colors[index],
                                      values[2], limits$chroma_floor))
    }
  }
  failures
}

grade_separation <- function(value, label, limits) {
  if (value < limits$cvd_floor) {
    return(list(failure = sprintf("%s: worst colour-vision dE %.1f is below %s", label, value, limits$cvd_floor)))
  }
  if (value < limits$cvd_target) {
    return(list(warning = sprintf("%s: worst colour-vision dE %.1f is below %s; use labels or gaps as a second cue",
                                  label, value, limits$cvd_target)))
  }
  list()
}

#' Check a palette for readability
#'
#' Runs hairline's palette checks: lightness band, chroma floor, separation
#' under simulated protanopia and deuteranopia, normal-vision separation, and
#' contrast against the surface.
#'
#' @param colors Character vector of hex colours, in slot order.
#' @param surface Background colour.
#' @param pairs `"adjacent"` for bars, stacks and lines; `"all"` for scatter plots and small multiples.
#' @return A list with `passed`, `worst_cvd`, `worst_normal`, `head_all_pairs`, `light_slots`, `warnings`, `failures`.
#' @examples
#' hl_check_palette(hl_palette(n = 4))
#' hl_check_palette(c("#1f77b4", "#2b83c4"), pairs = "all")
#' @export
hl_check_palette <- function(colors, surface = "#ffffff", pairs = c("adjacent", "all")) {
  pairs <- match.arg(pairs)
  for (color in c(colors, surface)) parse_hex(color)
  limits <- hl_tokens()$checks
  head_count <- min(length(colors), limits$head_slots)
  cvd <- worst_cvd(colors, pair_indices(length(colors), pairs))
  normal <- worst_normal(colors, pair_indices(length(colors), pairs))
  head <- worst_cvd(colors[seq_len(head_count)], pair_indices(head_count, "all"))
  graded <- c(grade_separation(cvd, paste(pairs, "pairs"), limits),
              grade_separation(head, sprintf("first %d slots", limits$head_slots), limits))
  failures <- c(band_failures(colors, limits), unlist(graded[names(graded) == "failure"], use.names = FALSE))
  if (normal < limits$normal_floor) {
    failures <- c(failures, sprintf("normal vision: worst dE %.1f is below %s", normal, limits$normal_floor))
  }
  light <- which(vapply(colors, contrast_ratio, numeric(1), second = surface) < limits$contrast_light_slot)
  list(passed = length(failures) == 0, worst_cvd = cvd, worst_normal = normal, head_all_pairs = head,
       light_slots = unname(light), warnings = unlist(graded[names(graded) == "warning"], use.names = FALSE) %||%
         character(), failures = failures)
}
