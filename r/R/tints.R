# Tints of a parent colour for its children (nested donut rings, partition bars).

tints <- function(colour, count) {
  rules <- hl_tokens()$tints
  values <- hex_to_oklch(colour)
  step <- min(rules$step, max(rules$cap - values[1], 0) / max(count, 1))
  vapply(seq_len(count), function(index) oklch_to_hex(values[1] + step * index, values[2], values[3]), character(1))
}
