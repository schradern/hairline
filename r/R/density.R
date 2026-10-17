# Kernel density, quantiles, jitter and bracket stacking for distribution charts; the same algorithms as the
# Python package's stats/density.py and charts/raincloud.py.

density_quantiles <- function(values, probabilities) {
  as.numeric(stats::quantile(values, probabilities, type = 7, names = FALSE))
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
