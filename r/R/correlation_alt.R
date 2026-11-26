# The description of a correlation heatmap for its alt text: the pairs with the highest and lowest correlation, as
# their cells write them. Mirrors the Python package's charts/correlation_alt.py.

# "Correlation matrix. Highest: Age and SOFA (0.62); lowest: Age and GCS (-0.41)." over the lower triangle's pairs,
# reading row by row, the earlier column named first. As Python's correlation_description().
correlation_description <- function(spec) {
  names <- unlist(spec$names)
  cells <- do.call(rbind, lapply(seq_along(names), function(row) {
    if (row == 1) return(NULL)
    data.frame(row = row, column = seq_len(row - 1))
  }))
  pairs <- vapply(seq_len(nrow(cells)), function(index) {
    word("pair_name", first = names[cells$column[index]], second = names[cells$row[index]])
  }, "")
  values <- spec$matrix[cbind(cells$row, cells$column)]
  texts <- spec$texts[cbind(cells$row, cells$column)]
  alt_described("kind_correlation", alt_extremes(pairs, values, texts))
}
