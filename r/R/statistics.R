# Tests and fits the charts compute from raw data; base R where it has them, and a log-rank test that matches
# survival::survdiff without depending on it. The Python package computes the same values.

rank_sum_p <- function(first, second) {
  suppressWarnings(stats::wilcox.test(first, second, exact = FALSE, correct = TRUE)$p.value)
}

# As survival::survdiff, only groups with expected events take part, one of them left out of the quadratic form.
# With fewer than two such groups, or a singular variance (every event at one time), the test is undefined: p is NA.
logrank_test <- function(time, event, group) {
  labels <- unique(as.character(group))
  member <- outer(as.character(group), labels, "==")
  difference <- numeric(length(labels))
  expected <- numeric(length(labels))
  variance <- matrix(0, length(labels), length(labels))
  undefined <- list(chisq = NA_real_, df = length(labels) - 1L, p = NA_real_)
  for (moment in sort(unique(time[event == 1]))) {
    at_risk <- colSums(member & time >= moment)
    deaths <- colSums(member & time == moment & event == 1)
    n <- sum(at_risk)
    d <- sum(deaths)
    share <- at_risk / n
    expected <- expected + d * share
    difference <- difference + deaths - d * share
    if (n > 1) variance <- variance + d * (n - d) / (n - 1) * (diag(share, length(share)) - outer(share, share))
  }
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

kruskal_p <- function(samples) suppressWarnings(stats::kruskal.test(samples)$p.value)

chi_square_p <- function(counts) suppressWarnings(stats::chisq.test(counts, correct = FALSE)$p.value)
