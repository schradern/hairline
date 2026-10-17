# Label placement shared by the chart types: push overlapping labels apart along one direction.

isotonic <- function(values) {
  totals <- numeric()
  counts <- numeric()
  for (value in values) {
    totals <- c(totals, value)
    counts <- c(counts, 1)
    while (length(totals) > 1 && totals[length(totals) - 1] / counts[length(counts) - 1] >
             totals[length(totals)] / counts[length(counts)]) {
      last <- length(totals)
      totals[last - 1] <- totals[last - 1] + totals[last]
      counts[last - 1] <- counts[last - 1] + counts[last]
      totals <- totals[-last]
      counts <- counts[-last]
    }
  }
  rep(totals / counts, counts)
}

spread_labels <- function(positions, height, low, high) {
  count <- length(positions)
  if (count == 0) return(numeric())
  order <- order(positions, seq_len(count))
  ranks <- seq_len(count) - 1
  shifted <- isotonic(positions[order] - ranks * height)
  floor_value <- low
  ceiling_value <- high - (count - 1) * height
  shifted <- if (ceiling_value < floor_value) rep((floor_value + ceiling_value) / 2, count) else
    pmin(pmax(shifted, floor_value), ceiling_value)
  result <- numeric(count)
  result[order] <- shifted + ranks * height
  result
}
