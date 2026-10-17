# Tints of a parent colour for its children (nested donut rings, partition bars).

tints <- function(colour, count) {
  rules <- hl_tokens()$tints
  values <- hex_to_oklch(colour)
  direction <- if (values[1] + rules$step * count <= rules$cap) 1 else -1
  room <- if (direction > 0) rules$cap - values[1] else values[1] - rules$floor
  step <- min(rules$step, max(room, 0) / max(count, 1))
  vapply(seq_len(count), function(index) {
    oklch_to_hex(values[1] + direction * step * index, values[2], values[3])
  }, character(1))
}
