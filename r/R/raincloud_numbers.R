# The raincloud's numbers under the groups, mirroring the Python raincloud_numbers.py: rows of measures (stats =) and
# of comparisons (compare =), each value under its group, as the n row.

# The measures written under the groups; n has its own row (show_n), and panels have no row under them.
raincloud_check_stats <- function(stats, facet) {
  stats <- as_names(stats, "raincloud", "stats", summary_names)
  if (length(stats) && !is.null(facet)) {
    stop(paste("hairline: raincloud: stats writes a row of numbers under the groups, which facet panels do not have;",
               "use hl_spread(facet = ...), which lists the numbers beside each block's rows"), call. = FALSE)
  }
  stats
}

# One table row per measure, its label on the left, each group's number under the group.
raincloud_stat_rows <- function(groups, stats, percent) {
  if (!length(stats)) return(list())
  numbers <- measure_numbers(unlist(groups, use.names = FALSE), percent, NULL)
  found <- lapply(groups, stat_pairs, names = stats, numbers = numbers)
  lapply(seq_along(stats), function(row) {
    list(label = found[[1]][[row]][1], colour = NULL, x = seq_along(groups) - 1,
         text = unname(vapply(found, function(pairs) pairs[[row]][2], character(1))))
  })
}

# The delta and p rows under the groups, each against the reference or the group to its left, and the caption note
# naming the test, and each group's delta and p pairs (for its tooltip); none without compare. As Python's
# compare_rows().
raincloud_compare_rows <- function(groups, compare, facet, marks, percent) {
  compare <- check_compare(compare, names(groups), "raincloud")
  if (is.null(compare)) return(list(rows = list(), note = NULL, pairs = list()))
  if (!is.null(facet)) {
    stop(paste("hairline: raincloud: compare writes rows of numbers under the groups, which facet panels do not",
               "have; use hl_spread(facet = ..., compare = ...), which compares within each block"), call. = FALSE)
  }
  numbers <- measure_numbers(unlist(groups, use.names = FALSE), percent, NULL)
  method <- compare_method(marks)
  found <- comparison_pairs(groups, compare, method, numbers)
  rows <- lapply(1:2, function(row) {
    list(label = found[[1]][[row]][1], colour = NULL, x = seq_along(groups) - 1,
         text = unname(vapply(found, function(pairs) pairs[[row]][2], character(1))))
  })
  list(rows = rows, note = compare_caption(compare, method, length(groups) - 1), pairs = found)
}

# Each group's summary tooltip: the measures it draws and writes, its n, and its delta and p with compare, in the
# numbers' own digits (the measures of all groups set them, as for the rows under the groups). As Python's
# group_tips().
raincloud_group_tips <- function(groups, every, marks, stats, compared, percent) {
  numbers <- measure_numbers(every, percent, NULL)
  measures <- tip_measures(marks, stats)
  groups <- groups[lengths(groups) > 0]
  stats::setNames(lapply(names(groups), function(name) {
    pairs_tip(name, c(stat_pairs(groups[[name]], measures, numbers), compared[[name]]))
  }), names(groups))
}
