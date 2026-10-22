# Kaplan–Meier estimate with Greenwood variance and a 95 % band on the log scale (survival::survfit's default);
# the same algorithm as the Python package's km_estimate().

km_check_inputs <- function(time, event) {
  if (length(time) == 0 || length(time) != length(event)) {
    stop(sprintf(paste("hairline: Kaplan\u2013Meier needs as many times as events and at least one;",
                       "got %d times and %d events"), length(time), length(event)), call. = FALSE)
  }
  missing <- which(is.na(time) | is.na(event))
  if (length(missing)) {
    stop(sprintf("hairline: Kaplan\u2013Meier time and event must not be missing; row %d has time %s and event %s",
                 missing[1], format(time[missing[1]]), format(event[missing[1]])), call. = FALSE)
  }
  unknown <- setdiff(sort(unique(event)), c(0, 1))
  if (length(unknown)) {
    stop(sprintf("hairline: Kaplan\u2013Meier event values must be 0 or 1; found %s", format(unknown[1])),
         call. = FALSE)
  }
  if (any(time < 0)) {
    stop(sprintf("hairline: Kaplan\u2013Meier time %s is negative; times count from 0", format(time[time < 0][1])),
         call. = FALSE)
  }
}

# The band per time; undefined (NA) where the survival reached 0 or the variance is infinite.
km_band <- function(survival, variance) {
  spread <- stats::qnorm(0.975) * sqrt(variance)
  undefined <- survival <= 0 | is.infinite(variance)
  list(low = ifelse(undefined, NA_real_, survival * exp(-spread)),
       high = ifelse(undefined, NA_real_, pmin(1, survival * exp(spread))))
}

# One row per distinct time, counted in one pass over the sorted times (linear in the rows, as in Python).
km_estimate <- function(time, event) {
  time <- as.numeric(time)
  event <- as.numeric(event)
  km_check_inputs(time, event)
  moments <- sort(unique(time))
  position <- match(time, moments)
  leaving <- tabulate(position, length(moments))
  events <- tabulate(position[event == 1], length(moments))
  at_risk <- length(time) - c(0, utils::head(cumsum(leaving), -1))
  survival <- cumprod(ifelse(events > 0, 1 - events / at_risk, 1))
  variance <- cumsum(ifelse(events == 0, 0, ifelse(at_risk > events, events / (at_risk * (at_risk - events)), Inf)))
  limits <- km_band(survival, variance)
  data.frame(time = moments, at_risk = at_risk, events = events, censored = leaving - events, survival = survival,
             low = limits$low, high = limits$high)
}

median_tolerance <- sqrt(.Machine$double.eps)

# Decimals for medians: one, or more where the times are small (0.02 years is not 0.0).
median_digits <- function(tables) {
  times <- unlist(lapply(tables, function(table) table$time))
  max(1, auto_digits(times[times > 0]))
}

# First time the survival reaches 50 % or less; where the curve stays at exactly 50 %, the middle between that time
# and its next drop (survival::survfit's rule). NULL when the curve stays above.
km_median <- function(table) {
  keep <- table$survival < 0.5 + median_tolerance
  if (!any(keep)) return(NULL)
  times <- table$time[keep]
  survival <- table$survival[keep]
  lower <- which(survival < survival[1])
  if (abs(survival[1] - 0.5) < median_tolerance && length(lower)) return((times[1] + times[lower[1]]) / 2)
  times[1]
}

at_risk_at <- function(time, moments) vapply(moments, function(moment) sum(time >= moment), numeric(1))
