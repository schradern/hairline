# Tick positions shared with the Python package: 3 to 6 'nice' breaks; the data may pass the outer
# breaks by at most 10 % of the break range, and zero is preferred when the data starts near it.

padded_range <- function(low, high) {
  if (high > low) return(c(low, high))
  pad <- if (low != 0) abs(low) * 0.25 else 1
  c(low - pad, high + pad)
}

break_variants <- function(low, high, step, rules, wants_zero) {
  start <- floor(low / step + 1e-9) * step
  end <- ceiling(high / step - 1e-9) * step
  options <- list()
  for (first in c(start, start + step)) {
    for (last in c(end, end - step)) {
      extent <- last - first
      faces_zero <- wants_zero && ((low >= 0 && first > low + 1e-12) || (high <= 0 && last < high - 1e-12))
      if (extent > 0 && !faces_zero && first - low <= rules$overshoot_low * extent + 1e-12 &&
            high - last <= rules$overshoot_high * extent + 1e-12) {
        options[[length(options) + 1]] <- c(first, last)
      }
    }
  }
  unique(options)
}

misfit <- function(low, high, start, end, wants_zero) {
  floor_value <- if (wants_zero && low > 0) min(low, 0) else low
  ceiling_value <- if (wants_zero && high < 0) max(high, 0) else high
  empty <- max(0, floor_value - start) + max(0, end - ceiling_value)
  overshoot <- max(0, start - low) + max(0, high - end)
  round(max(empty, overshoot) / (end - start), 9)
}

near_zero <- function(low, high) {
  (low <= 0 && 0 <= high) || (low > 0 && low <= 0.5 * high) || (high < 0 && high >= 0.5 * low)
}

key_less <- function(key, other) {
  for (index in seq_along(key)) {
    if (key[index] != other[index]) return(key[index] < other[index])
  }
  FALSE
}

nice_breaks <- function(low, high, target = 5) {
  if (low > high) {
    stop(sprintf("hairline: nice_breaks got low %s is above high %s; pass the range in order",
                 format(low), format(high)), call. = FALSE)
  }
  rules <- hl_tokens()$ticks
  range <- padded_range(low, high)
  magnitude <- floor(log10(range[2] - range[1]))
  wants_zero <- near_zero(range[1], range[2])
  best <- NULL
  for (exponent in (magnitude - 1):(magnitude + 1)) {
    for (multiplier in rules$multipliers) {
      step <- multiplier * 10^exponent
      for (option in break_variants(range[1], range[2], step, rules, wants_zero)) {
        count <- round((option[2] - option[1]) / step) + 1
        if (count < rules$min || count > rules$max) next
        misses_zero <- wants_zero && !(option[1] <= 0 && 0 <= option[2])
        fit <- misfit(range[1], range[2], option[1], option[2], wants_zero)
        key <- c(abs(count - target), as.numeric(misses_zero), fit, option[2] - option[1], -step)
        if (is.null(best) || key_less(key, best$key)) best <- list(key = key, start = option[1], step = step,
                                                                   count = count)
      }
    }
  }
  signif(best$start + (seq_len(best$count) - 1) * best$step, 10)
}

axis_limits <- function(low, high, breaks) c(min(low, breaks[1]), max(high, breaks[length(breaks)]))

month_starts <- function(low, high, step) {
  first <- as.Date(format(low, "%Y-%m-01"))
  days <- seq(first, as.Date(format(high, "%Y-%m-01")), by = "month")
  days[days >= low & days <= high & (as.integer(format(days, "%m")) - 1) %% step == 0]
}

month_breaks <- function(low, high, target = 5) {
  best <- NULL
  for (step in hl_tokens()$ticks$month_steps) {
    days <- month_starts(low, high, step)
    if (length(days) >= 3 && length(days) <= 7 &&
          (is.null(best) || abs(length(days) - target) <= abs(length(best) - target))) {
      best <- days
    }
  }
  best %||% month_starts(low, high, 1)
}

month_label <- function(days, locale = NULL) {
  months <- locale_symbols(locale)$months
  month <- as.integer(format(days, "%m"))
  ifelse(month == 1, format(days, "%Y"), months[month])
}
