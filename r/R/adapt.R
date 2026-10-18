# Step brand colours into the readable band while keeping their hues.

snap_into_band <- function(color, limits) {
  values <- hex_to_oklch(color)
  c(min(limits$adapt_lightness[2], max(limits$adapt_lightness[1], values[1])),
    max(values[2], limits$adapt_chroma), values[3])
}

# The pair to separate next: lowest colour-vision dE (then normal dE); across all pairs, the pair furthest below
# either floor, so a normal-vision failure is fixed too.
weakest_pair <- function(colors, pairs = "adjacent") {
  limits <- hl_tokens()$checks
  candidates <- c(pair_indices(length(colors), pairs), pair_indices(min(3, length(colors)), "all"))
  best <- NULL
  best_key <- NULL
  for (pair in candidates) {
    a <- colors[pair[1]]
    b <- colors[pair[2]]
    vision <- min(delta_e(a, b, "protan"), delta_e(a, b, "deutan"))
    normal <- delta_e(a, b)
    key <- if (pairs == "all") c(min(vision / limits$cvd_floor, normal / limits$normal_floor), vision) else
      c(vision, normal)
    if (is.null(best_key) || key[1] < best_key[1] || (key[1] == best_key[1] && key[2] < best_key[2])) {
      best <- pair
      best_key <- key
    }
  }
  best
}

nudge_slots <- function(slots, pair, limits) {
  lightness <- vapply(pair, function(index) slots[[index]][1], numeric(1))
  ordered <- pair[order(-lightness)]
  lighter <- ordered[1]
  darker <- ordered[2]
  if (slots[[lighter]][1] + limits$adapt_step <= limits$adapt_lightness[2]) {
    slots[[lighter]][1] <- slots[[lighter]][1] + limits$adapt_step
  } else {
    slots[[darker]][1] <- slots[[darker]][1] - limits$adapt_step
  }
  slots
}

slots_to_hex <- function(slots) vapply(slots, function(slot) oklch_to_hex(slot[1], slot[2], slot[3]), character(1))

adapt_readable <- function(colors, pairs = "adjacent") {
  if (hl_check_palette(colors, pairs = pairs)$passed) return(colors)
  limits <- hl_tokens()$checks
  slots <- lapply(colors, snap_into_band, limits = limits)
  for (iteration in seq_len(limits$adapt_iterations)) {
    adapted <- slots_to_hex(slots)
    if (hl_check_palette(adapted, pairs = pairs)$passed) return(adapted)
    slots <- nudge_slots(slots, weakest_pair(adapted, pairs), limits)
  }
  adapted <- slots_to_hex(slots)
  remaining <- hl_check_palette(adapted, pairs = pairs)$failures
  if (length(remaining) > 0) {
    warning(sprintf("hairline: colours could not be made fully readable: %s", paste(remaining, collapse = "; ")),
            call. = FALSE)
  }
  adapted
}
