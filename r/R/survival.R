# Kaplan–Meier estimate with Greenwood variance and a 95 % band on the log scale (survival::survfit's default);
# the same algorithm as the Python package's km_estimate().

km_check_inputs <- function(time, event) {
  if (length(time) == 0 || length(time) != length(event)) {
    stop(sprintf("hairline: Kaplan–Meier needs as many times as events and at least one; got %d times and %d events",
                 length(time), length(event)), call. = FALSE)
  }
  unknown <- setdiff(sort(unique(event)), c(0, 1))
  if (length(unknown)) {
    stop(sprintf("hairline: Kaplan–Meier event values must be 0 or 1; found %s", format(unknown[1])), call. = FALSE)
  }
  if (any(time < 0)) {
    stop(sprintf("hairline: Kaplan–Meier time %s is negative; times count from 0", format(time[time < 0][1])),
         call. = FALSE)
  }
}

km_band <- function(survival, variance) {
  if (survival <= 0 || is.infinite(variance)) return(c(NA_real_, NA_real_))
  spread <- stats::qnorm(0.975) * sqrt(variance)
  c(survival * exp(-spread), min(1, survival * exp(spread)))
}

km_estimate <- function(time, event) {
  time <- as.numeric(time)
  event <- as.numeric(event)
  km_check_inputs(time, event)
  survival <- 1
  variance <- 0
  rows <- list()
  for (moment in sort(unique(time))) {
    at_risk <- sum(time >= moment)
    events <- sum(time == moment & event == 1)
    if (events > 0) {
      survival <- survival * (1 - events / at_risk)
      variance <- variance + if (at_risk > events) events / (at_risk * (at_risk - events)) else Inf
    }
    limits <- km_band(survival, variance)
    rows[[length(rows) + 1]] <- data.frame(time = moment, at_risk = at_risk, events = events,
                                           censored = sum(time == moment & event == 0), survival = survival,
                                           low = limits[1], high = limits[2])
  }
  do.call(rbind, rows)
}

km_median <- function(table) {
  reached <- table$time[table$survival <= 0.5]
  if (length(reached)) reached[1] else NULL
}

at_risk_at <- function(time, moments) vapply(moments, function(moment) sum(time >= moment), numeric(1))
