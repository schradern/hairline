# compare =, mirroring the Python comparisons.py: each group against a reference group or the group before it, written
# as numbers beside the others (never over the data): the difference with its 95% CI and p, the test named in the
# caption. The test follows the chart's centre: with the median the Hodges-Lehmann shift (distribution-free CI) and
# the Wilcoxon rank-sum p, with the mean alone the difference in means and Welch's t-test.

compare_adjacent <- "adjacent"
# Pairwise differences the shift computes at most (two groups of 3,000 values); beyond, its CI is left out.
compare_max_pairs <- 9e6

# A group to compare against, or "adjacent"; NULL compares nothing.
check_compare <- function(compare, names, chart) {
  if (is.null(compare)) return(NULL)
  compare <- as.character(compare)
  if (identical(compare, "all")) {
    stop(sprintf(paste("hairline: %s: compare = \"all\" would need a number for every pair, which no row can hold;",
                       "compare against one group (compare = \"%s\") or \"adjacent\""), chart, names[1]), call. = FALSE)
  }
  if (!identical(compare, compare_adjacent) && !compare %in% names) {
    stop(sprintf("hairline: %s: compare names '%s', which is not a group; use 'adjacent' or one of: %s", chart,
                 compare, paste(names, collapse = ", ")), call. = FALSE)
  }
  compare
}

# "means" when the chart's centre is the mean alone, "shift" (rank-based) otherwise.
compare_method <- function(marks) if ("mean" %in% marks && !"median" %in% marks) "means" else "shift"

# Difference in means (first minus second) with Welch's 95% CI and two-sided p; NaN where a group has fewer than two
# values or neither varies. As stats::t.test().
welch_difference <- function(first, second) {
  difference <- mean(first) - mean(second)
  undefined <- list(estimate = difference, low = NaN, high = NaN, p = NaN)
  if (length(first) < 2 || length(second) < 2) return(undefined)
  share_x <- stats::var(first) / length(first)
  share_y <- stats::var(second) / length(second)
  error <- sqrt(share_x + share_y)
  if (error == 0) return(undefined)
  freedom <- (share_x + share_y)^2 / (share_x^2 / (length(first) - 1) + share_y^2 / (length(second) - 1))
  half <- stats::qt(0.975, freedom) * error
  list(estimate = difference, low = difference - half, high = difference + half,
       p = min(1, 2 * stats::pt(-abs(difference) / error, freedom)))
}

# Hodges-Lehmann shift (first minus second): the median of every pairwise difference, its distribution-free 95% CI
# from the order statistics of those differences (normal approximation, as Bauer 1972), and the rank-sum p.
shift_difference <- function(first, second) {
  pairs <- length(first) * length(second)
  p <- rank_sum_p(first, second)
  if (pairs > compare_max_pairs) {
    return(list(estimate = stats::median(first) - stats::median(second), low = NaN, high = NaN, p = p))
  }
  differences <- sort(as.vector(outer(first, second, "-")))
  estimate <- stats::median(differences)
  rank <- floor(pairs / 2 - stats::qnorm(0.975) * sqrt(pairs * (length(first) + length(second) + 1) / 12))
  if (rank < 1) return(list(estimate = estimate, low = NaN, high = NaN, p = p))
  list(estimate = estimate, low = differences[rank], high = differences[pairs - rank + 1], p = p)
}

# A p as a key number's value: "0.004", "< 0.001"; a dash where the test is undefined.
p_text <- function(value) {
  if (is.na(value)) return("\u2013")
  sub("^= ", "", sub("^p ", "", format_p(value)))
}

difference_text <- function(found, numbers, method) {
  number <- if (method == "means") numbers[[2]] else numbers[[1]]
  if (is.na(found$low)) return(number(found$estimate))
  sprintf("%s [%s; %s]", number(found$estimate), number(found$low), number(found$high))
}

# Each group's delta and p as key-number pairs, in the groups' order: against the reference ("Reference" on its own
# row) or against the group before it (a dash on the first). A reference absent here leaves dashes.
comparison_pairs <- function(groups, compare, method, numbers) {
  label <- word("difference")
  dash <- "\u2013"
  names <- names(groups)
  stats::setNames(lapply(seq_along(groups), function(index) {
    name <- names[index]
    other <- if (identical(compare, compare_adjacent)) {
      if (index > 1) names[index - 1]
    } else {
      compare
    }
    if (!identical(compare, compare_adjacent) && name == compare) {
      return(list(c(label, word("reference_group")), c("p", dash)))
    }
    if (is.null(other) || !other %in% names || !length(groups[[index]]) || !length(groups[[other]])) {
      return(list(c(label, dash), c("p", dash)))
    }
    test <- (if (method == "means") welch_difference else shift_difference)(as.numeric(groups[[index]]),
                                                                            as.numeric(groups[[other]]))
    list(c(label, difference_text(test, numbers, method)), c("p", p_text(test$p)))
  }), names)
}

# The test named for the caption, and that several p values are not adjusted.
compare_caption <- function(compare, method, comparisons) {
  adjacent <- identical(compare, compare_adjacent)
  against <- if (adjacent) word("against_previous") else word("against_group", name = compare)
  text <- word(paste0("compare_", method), against = against)
  if (comparisons > 1) paste(text, word("unadjusted")) else text
}

# Rows drawn in sections (spread, dot plot blocks, ridgeline panels): each section's groups compared within it, in row
# order, their delta and p added to each row's pairs; the caption note naming the test, NULL without compare.
# `group_names` names a row's group where its key differs (a facet's "2025 . Unit A" is the group "Unit A").
section_comparisons <- function(rows, values, compare, marks, numbers, chart, group_names = NULL) {
  shown <- function(key) if (!is.null(group_names) && key %in% names(group_names)) group_names[[key]] else key
  keys <- vapply(rows, `[[`, character(1), "name")
  compare <- check_compare(compare, unique(vapply(keys, shown, character(1))), chart)
  if (is.null(compare)) return(list(rows = rows, note = NULL))
  method <- compare_method(marks)
  sections <- vapply(rows, function(row) as.character(row$section %||% ""), character(1))
  count <- 0
  for (section in unique(sections)) {
    members <- which(sections == section)
    groups <- stats::setNames(lapply(keys[members], function(key) values[[key]]),
                              vapply(keys[members], shown, character(1)))
    found <- comparison_pairs(groups, compare, method, numbers)
    for (position in seq_along(members)) {
      index <- members[position]
      rows[[index]]$pairs <- c(rows[[index]]$pairs, found[[position]])
      text <- found[[position]][[1]][2]
      count <- count + (text != "\u2013" && text != word("reference_group"))
    }
  }
  list(rows = rows, note = compare_caption(compare, method, count))
}
