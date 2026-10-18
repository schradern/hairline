# Tests and fits the charts compute from raw data; base R where it has them, and a log-rank test that matches
# survival::survdiff without depending on it. The Python package computes the same values.

rank_sum_p <- function(first, second) {
  stats::wilcox.test(first, second, exact = FALSE, correct = TRUE)$p.value
}

logrank_test <- function(time, event, group) {
  labels <- unique(as.character(group))
  member <- vapply(labels, function(label) as.character(group) == label, logical(length(group)))
  difference <- numeric(length(labels))
  variance <- matrix(0, length(labels), length(labels))
  for (moment in sort(unique(time[event == 1]))) {
    at_risk <- colSums(member & time >= moment)
    deaths <- colSums(member & time == moment & event == 1)
    n <- sum(at_risk)
    d <- sum(deaths)
    share <- at_risk / n
    difference <- difference + deaths - d * share
    if (n > 1) variance <- variance + d * (n - d) / (n - 1) * (diag(share, length(share)) - outer(share, share))
  }
  keep <- seq_len(length(labels) - 1)
  statistic <- as.numeric(t(difference[keep]) %*% solve(variance[keep, keep, drop = FALSE], difference[keep]))
  list(chisq = statistic, df = length(keep), p = stats::pchisq(statistic, length(keep), lower.tail = FALSE))
}

linear_fit <- function(x, y) {
  model <- stats::lm(y ~ x)
  residual <- summary(model)$sigma
  list(slope = unname(stats::coef(model)[2]), intercept = unname(stats::coef(model)[1]),
       slope_se = summary(model)$coefficients[2, 2], residual = residual, count = length(x), mean_x = mean(x),
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

egger_p <- function(estimate, se) {
  model <- stats::lm(I(estimate / se) ~ I(1 / se))
  summary(model)$coefficients[1, 4]
}

format_p <- function(value, locale = NULL) {
  if (value < 0.001) return(paste("p <", hl_format_number(0.001, 3, locale)))
  paste("p =", hl_format_number(value, if (value < 0.1) 3 else 2, locale))
}

kruskal_p <- function(samples) stats::kruskal.test(samples)$p.value

chi_square_p <- function(counts) suppressWarnings(stats::chisq.test(counts, correct = FALSE)$p.value)
