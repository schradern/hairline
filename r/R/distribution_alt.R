# The description of a distribution chart (spread, raincloud, ridgeline) for its alt text: the groups whose centre is
# highest and lowest, the centre the chart draws, written as its numbers write it. Mirrors the Python package's
# charts/distribution_alt.py.

# The centre the chart draws: the mean where it draws the mean and no median, else the median.
distribution_centre <- function(marks) if ("mean" %in% marks && !"median" %in% marks) "mean" else "median"

# Every panel's groups in reading order (`panels`: a list of list(name, groups), groups a named list of values), each
# named with its panel's name where there is one ("2025 · ICU", as the captions name a facet's rows; the separator is
# written here, not kept in a constant, so it stays UTF-8 whatever locale the package was installed in). As Python's
# facet_named().
distribution_facet_named <- function(panels) {
  unlist(lapply(panels, function(panel) {
    groups <- panel$groups
    if (!is.null(panel$name)) names(groups) <- paste(panel$name, "\u00b7", names(groups))
    groups
  }), recursive = FALSE)
}

# "Interval plot. Highest median: ICU (12.5); lowest: Ward (7.0)." over the groups with values (a named list), their
# centre in the digits the chart's numbers take from `every`. As Python's distribution_description().
distribution_description <- function(kind, groups, marks, every, percent, digits = NULL, discrete = FALSE) {
  centre <- distribution_centre(marks)
  numbers <- measure_numbers(as.numeric(every), percent, digits, discrete)
  groups <- groups[vapply(groups, length, integer(1)) > 0]
  values <- vapply(groups, function(values) as.numeric(summary_values(values, discrete)[[centre]]), numeric(1))
  texts <- vapply(groups, function(values) stat_pairs(values, centre, numbers, discrete)[[1]][2], character(1))
  alt_described(kind, alt_extremes(names(groups), unname(values), unname(texts), alt_centre_words,
                                   centre = word(paste0("centre_", centre))))
}
