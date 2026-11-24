# Histogram bins a reader can name: a round width (1, 2, 2.5 or 5 times a power of ten), edges on its multiples. As
# the Python package's stats/histogram.py.

# The round width nearest `raw` on a log scale (5.4 years gives 5, not 10); whole numbers keep whole widths (no 2.5
# years).
round_bin_width <- function(raw, whole) {
  multipliers <- hl_tokens()$ticks$multipliers
  if (whole) multipliers <- multipliers[multipliers != 2.5]
  power <- 10^floor(log10(raw))
  candidates <- c(multipliers, 10) * power
  width <- candidates[which.min(abs(log(candidates / raw)))]
  if (whole) max(width, 1) else width
}

# Freedman-Diaconis width, kept between the fewest and most bins the tokens allow, then rounded.
bin_width <- function(values, whole) {
  rules <- hl_tokens()$profile
  span <- max(values) - min(values)
  if (span <= 0) return(1)
  quartiles <- density_quantiles(values, c(0.25, 0.75))
  raw <- if (quartiles[2] > quartiles[1]) 2 * diff(quartiles) / length(values)^(1 / 3) else span / rules$min_bins
  raw <- min(max(raw, span / rules$max_bins), span / rules$min_bins)
  round_bin_width(raw, whole)
}

# Edges of round bins covering every value; each bin holds [edge, next edge). Bins one whole number wide sit on it
# (a stay of 4 days spans 3.5 to 4.5), wider bins start on their multiple.
bin_edges <- function(values, whole) {
  width <- bin_width(values, whole)
  offset <- if (whole && width == 1) 0.5 else 0
  start <- floor(min(values) / width + offset) * width - offset
  count <- floor((max(values) - start) / width + 1e-9) + 1
  start + width * seq(0, count)
}

# How many values fall in each bin of `edges` (none for an empty group).
counts_in <- function(values, edges) {
  if (!length(values)) return(rep(0L, length(edges) - 1))
  as.integer(table(cut(values, edges, right = FALSE, include.lowest = FALSE)))
}
