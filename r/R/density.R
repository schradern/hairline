# Kernel density, quantiles, jitter and bracket stacking for distribution charts; the same algorithms as the
# Python package's stats/density.py and charts/raincloud.py.

density_quantiles <- function(values, probabilities) {
  as.numeric(stats::quantile(values, probabilities, type = 7, names = FALSE))
}

# Quantiles that stay on the data's levels (type 1, numpy's inverted_cdf): the smallest value reached by at least that
# share of the values. Of daily peaks, the 0.9 quantile is the staffing that is enough on 9 of 10 days; of counts of
# people, the median is a whole person.
level_quantiles <- function(values, probabilities) {
  as.numeric(stats::quantile(values, probabilities, type = 1, names = FALSE))
}

# The two levels a median falls between when it matches neither and each holds more than `share` of the values (doses
# of 25 and 50 mg, median 35); NULL otherwise, and for fewer than `least` values, whose median falls between two of
# them by chance.
median_gap <- function(values, share, least = 10) {
  values <- as.numeric(values)
  if (length(values) < least) return(NULL)
  middle <- stats::median(values)
  below <- values[values < middle]
  above <- values[values > middle]
  if (!length(below) || !length(above) || any(values == middle)) return(NULL)
  low <- max(below)
  high <- min(above)
  if (mean(values == low) > share && mean(values == high) > share) c(low, high) else NULL
}

# The `count` most frequent values with their shares, most frequent first (ties: the smaller value first).
top_levels <- function(values, count) {
  values <- as.numeric(values)
  levels <- sort(unique(values))
  found <- tabulate(match(values, levels), length(levels))
  ranked <- order(-found, levels)[seq_len(min(count, length(levels)))]
  data.frame(level = levels[ranked], share = found[ranked] / length(values))
}

density_bandwidth <- function(values) {
  limits <- density_quantiles(values, c(0.25, 0.75))
  spread <- min(stats::sd(values), (limits[2] - limits[1]) / 1.34)
  if (spread == 0) {
    spread <- stats::sd(values)
    if (spread == 0) spread <- abs(values[1])
    if (spread == 0) spread <- 1
  }
  0.9 * spread * length(values)^(-0.2)
}

density_curve <- function(values, points = 128) {
  values <- as.numeric(values)
  if (length(unique(values)) < 2) return(NULL)
  width <- density_bandwidth(values)
  grid <- seq(min(values), max(values), length.out = points)
  height <- vapply(grid, function(level) sum(exp(-0.5 * ((level - values) / width)^2)), numeric(1)) /
    (length(values) * width * sqrt(2 * pi))
  list(grid = grid, height = height)
}

jitter_offsets <- function(count) ((seq_len(count) * 0.618034) %% 1) - 0.5

bracket_levels <- function(spans) {
  widths <- vapply(spans, function(span) abs(span[2] - span[1]), numeric(1))
  levels <- integer(length(spans))
  taken <- list()
  for (index in order(widths, seq_along(spans))) {
    span <- sort(spans[[index]])
    level <- 0L
    while (any(vapply(taken, function(other) {
      other$level == level && !(span[2] < other$low || span[1] > other$high)
    }, logical(1)))) {
      level <- level + 1L
    }
    levels[index] <- level
    taken[[length(taken) + 1]] <- list(level = level, low = span[1], high = span[2])
  }
  levels
}
