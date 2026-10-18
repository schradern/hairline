# The ramp rule, mirroring the Python package's color/ramps: sequential ramps from one hue,
# diverging ramps from two, in OKLCH. The token ramps and a brand's ramps both come from here.

# Light to dark in one hue (NULL: greys); chroma peaks in the middle steps.
sequential_ramp <- function(hue, definition = hl_tokens()$ramp_definitions) {
  steps <- definition$steps
  light <- definition$lightness[1]
  dark <- definition$lightness[2]
  vapply(seq_len(steps) - 1, function(index) {
    lightness <- light + (dark - light) * index / (steps - 1)
    envelope <- 0.35 + 0.65 * sin(pi * (0.15 + 0.7 * index / (steps - 1)))
    chroma <- if (is.null(hue)) 0 else definition$chroma_peak * envelope
    oklch_to_hex(lightness, chroma, hue %||% 0)
  }, character(1))
}

# The low arm dark to light, the neutral midpoint, the high arm light to dark.
diverging_ramp <- function(low_hue, high_hue, definition = hl_tokens()$ramp_definitions) {
  low <- sequential_ramp(low_hue, definition)
  high <- sequential_ramp(high_hue, definition)
  c(rev(low[-1]), definition$midpoint, high[-1])
}

# The brand's ramps: `sequential` and `diverging` hues, else the hues of its first one and two colours.
brand_ramps <- function(brand) {
  used <- brand$colors_used
  hue <- brand$sequential_hue %||% if (length(used)) hex_to_oklch(used[1])[3] else NULL
  pair <- brand$diverging_hues %||% if (length(used) > 1) c(hex_to_oklch(used[1])[3], hex_to_oklch(used[2])[3])
  ramps <- list()
  if (!is.null(hue)) ramps[["brand-sequential"]] <- sequential_ramp(hue)
  if (!is.null(pair)) ramps[["brand-diverging"]] <- diverging_ramp(pair[1], pair[2])
  ramps
}

# `defaults: hairline: sequential:` (one colour) and `diverging:` (two), as palette names or hex values.
brand_ramp_hues <- function(content, palette, path) {
  sequential <- brand_get(content, "defaults.hairline.sequential")
  diverging <- brand_get(content, "defaults.hairline.diverging")
  if (!is.null(diverging) && length(diverging) != 2) {
    brand_fail(path, "defaults.hairline.diverging", "must list two colours, the low and the high pole")
  }
  hue_of <- function(value, key) hex_to_oklch(brand_color(value, key, palette, path))[3]
  list(sequential = if (!is.null(sequential)) hue_of(sequential, "defaults.hairline.sequential"),
       diverging = if (!is.null(diverging)) vapply(unlist(diverging), hue_of, numeric(1),
                                                   key = "defaults.hairline.diverging", USE.NAMES = FALSE))
}
