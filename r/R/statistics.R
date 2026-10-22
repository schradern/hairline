# Tests and fits the charts compute from raw data; base R where it has them, and a log-rank test that matches
# survival::survdiff without depending on it. The Python package computes the same values.

# Two-sided Wilcoxon rank-sum p by the normal approximation with tie and continuity correction, as
# wilcox.test(exact = FALSE, correct = TRUE) defines it, with both tails from pnorm(-|z|): wilcox.test() itself returns
# 0 for a far tail in one order of the samples and not the other. NA when every value ties (the test is undefined).
rank_sum_p <- function(first, second) {
  if (length(unique(c(first, second))) < 2) return(NA_real_)
  count_x <- length(first)
  count_y <- length(second)
  total <- count_x + count_y
  ranks <- rank(c(first, second))
  ties <- as.numeric(table(ranks))
  sigma <- sqrt(count_x * count_y / 12 * ((total + 1) - sum(ties^3 - ties) / (total * (total - 1))))
  shift <- sum(ranks[seq_len(count_x)]) - count_x * (count_x + 1) / 2 - count_x * count_y / 2
  min(1, 2 * stats::pnorm(-abs((shift - sign(shift) * 0.5) / sigma)))
}

# W as wilcox.test() reports it (the first sample's rank sum less its minimum) and the rank-sum p.
rank_sum_test <- function(first, second) {
  ranks <- rank(c(first, second))
  statistic <- sum(ranks[seq_along(first)]) - length(first) * (length(first) + 1) / 2
  list(statistic = statistic, p = rank_sum_p(first, second))
}

# As survival::survdiff, only groups with expected events take part, one of them left out of the quadratic form.
# With fewer than two such groups, or a singular variance (every event at one time), the test is undefined: p is NA.
# Each group's number at risk and deaths at every event time are counted from its sorted times at once, so the test
# is linear in the rows.
logrank_test <- function(time, event, group) {
  group <- as.character(group)
  labels <- unique(group)
  undefined <- list(chisq = NA_real_, df = length(labels) - 1L, p = NA_real_)
  moments <- sort(unique(time[event == 1]))
  if (!length(moments)) return(undefined)
  at_risk <- matrix(vapply(labels, function(label) {
    times <- sort(time[group == label])
    as.numeric(length(times) - findInterval(moments, times, left.open = TRUE))
  }, numeric(length(moments))), nrow = length(moments))
  deaths <- matrix(vapply(labels, function(label) {
    as.numeric(tabulate(match(time[group == label & event == 1], moments), length(moments)))
  }, numeric(length(moments))), nrow = length(moments))
  n <- rowSums(at_risk)
  d <- rowSums(deaths)
  share <- at_risk / n
  expected <- colSums(d * share)
  difference <- colSums(deaths) - expected
  weight <- ifelse(n > 1, d * (n - d) / (n - 1), 0)
  variance <- diag(colSums(weight * share), length(labels)) - crossprod(share * weight, share)
  kept <- which(expected > 0)
  if (length(kept) < 2) return(undefined)
  used <- kept[-1]
  solved <- tryCatch(solve(variance[used, used, drop = FALSE], difference[used]), error = function(error) NULL)
  if (is.null(solved)) return(undefined)
  statistic <- sum(difference[used] * solved)
  list(chisq = statistic, df = length(used), p = stats::pchisq(statistic, length(used), lower.tail = FALSE))
}

linear_fit <- function(x, y) {
  model <- stats::lm(y ~ x)
  # A perfect fit (constant y) is a valid line; summary() would only warn about it.
  fitted <- suppressWarnings(summary(model))
  list(slope = unname(stats::coef(model)[2]), intercept = unname(stats::coef(model)[1]),
       slope_se = fitted$coefficients[2, 2], residual = fitted$sigma, count = length(x), mean_x = mean(x),
       spread = sum((x - mean(x))^2), t = stats::qt(0.975, length(x) - 2))
}

fit_band <- function(fit, xs) {
  centre <- fit$intercept + fit$slope * xs
  half <- fit$t * fit$residual * sqrt(1 / fit$count + (xs - fit$mean_x)^2 / fit$spread)
  list(centre = centre, low = centre - half, high = centre + half)
}

pearson_test <- function(x, y, method = "pearson") {
  test <- suppressWarnings(stats::cor.test(x, y, method = method, exact = FALSE))
  if (method == "spearman") {
    r <- stats::cor(rank(x), rank(y))
    p <- 2 * stats::pt(-abs(r * sqrt((length(x) - 2) / (1 - r^2))), length(x) - 2)
    return(c(r, p))
  }
  c(unname(test$estimate), test$p.value)
}

# NA (undefined) with fewer than three studies, one standard error for all, or a perfect fit.
egger_p <- function(estimate, se) {
  if (length(se) < 3 || length(unique(se)) < 2) return(NA_real_)
  model <- stats::lm(I(estimate / se) ~ I(1 / se))
  p <- suppressWarnings(summary(model)$coefficients[1, 4])
  if (is.finite(p)) p else NA_real_
}

# The log-rank p as key-number text over the given rows; NULL when no event makes the test undefined.
logrank_text <- function(time, event, group) {
  p <- logrank_test(time, event, group)$p
  if (is.na(p)) NULL else format_p(p)
}

# NA or NaN (a test that all-equal values leave undefined) reads "p not defined".
format_p <- function(value, locale = NULL) {
  if (is.na(value)) return("p not defined")
  if (value < 0.001) return(paste("p <", hl_format_number(0.001, 3, locale)))
  paste("p =", hl_format_number(value, if (value < 0.1) 3 else 2, locale))
}

kruskal_p <- function(samples) {
  if (length(unique(unlist(samples))) < 2) return(NA_real_)
  suppressWarnings(stats::kruskal.test(samples)$p.value)
}

# H, degrees of freedom and p; H and p are NA when every value ties.
kruskal_test <- function(samples) {
  df <- length(samples) - 1L
  if (length(unique(unlist(samples))) < 2) return(list(statistic = NA_real_, df = df, p = NA_real_))
  test <- suppressWarnings(stats::kruskal.test(samples))
  list(statistic = unname(test$statistic), df = df, p = test$p.value)
}

chi_square_p <- function(counts) suppressWarnings(stats::chisq.test(counts, correct = FALSE)$p.value)

sparse_expected <- 5

# The test for a table of counts, after dropping categories and groups without any count: Fisher's exact test for a
# 2 x 2 table with an expected count below 5, where chi-squared is unreliable, Pearson's chi-squared otherwise. NULL
# when fewer than two categories or groups remain.
contingency_test <- function(counts) {
  counts <- as.matrix(counts)
  counts <- counts[rowSums(counts) > 0, colSums(counts) > 0, drop = FALSE]
  if (min(dim(counts)) < 2) return(NULL)
  expected <- outer(rowSums(counts), colSums(counts)) / sum(counts)
  if (all(dim(counts) == 2) && any(expected < sparse_expected)) {
    return(list(method = "Fisher's exact test", statistic = NA_real_, df = NA_integer_,
                p = stats::fisher.test(counts)$p.value))
  }
  c(list(method = "Chi-squared"), chi_square_test(counts))
}

chi_square_test <- function(counts) {
  test <- suppressWarnings(stats::chisq.test(counts, correct = FALSE))
  list(statistic = unname(test$statistic), df = unname(test$parameter), p = test$p.value)
}
