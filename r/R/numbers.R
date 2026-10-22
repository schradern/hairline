# Locale-aware number formatting shared with the Python package.

locale_symbols <- function(locale) {
  locales <- hl_tokens()$locales
  locale <- locale %||% (hl_settings()$locale %||% hl_tokens()$default_locale)
  if (!locale %in% names(locales)) {
    stop(sprintf("hairline: unknown locale '%s'; available locales: %s", locale,
                 paste(sort(names(locales)), collapse = ", ")), call. = FALSE)
  }
  locales[[locale]]
}

group_thousands <- function(integer_part, separator) {
  groups <- character()
  while (nchar(integer_part) > 3) {
    groups <- c(substring(integer_part, nchar(integer_part) - 2), groups)
    integer_part <- substring(integer_part, 1, nchar(integer_part) - 3)
  }
  paste(c(integer_part, groups), collapse = separator)
}
rounding_tolerance <- 1e-9
significant_digits <- 15
missing_text <- "\u2013"

# `magnitude` (zero or more) with `digits` decimals, halves rounded up in decimal. The value is read to the 15
# significant digits a double holds, so float noise beyond them does not decide (8.649999999999999 is 8.65, the
# stored 8.645 is a half) and exact values stay exact at any size (1,000,000,000 and 999,999,999,999.4). Digits past
# the fifteenth read as zeros, as in the Python package.
fixed_text <- function(magnitude, digits) {
  parts <- strsplit(sprintf("%.*e", significant_digits - 1L, magnitude), "e", fixed = TRUE)[[1]]
  mantissa <- sub(".", "", parts[1], fixed = TRUE)
  keep <- as.integer(parts[2]) + 1L + digits
  units <- if (keep >= significant_digits) {
    paste0(mantissa, strrep("0", keep - significant_digits))
  } else if (keep < 0) {
    "0"
  } else {
    kept <- if (keep > 0) as.numeric(substr(mantissa, 1, keep)) else 0
    up <- as.integer(substr(mantissa, keep + 1L, keep + 1L)) >= 5
    sprintf("%.0f", kept + up)
  }
  units <- sub("^0+(?=[0-9])", "", units, perl = TRUE)
  if (digits == 0) return(units)
  units <- paste0(strrep("0", max(0, digits + 1 - nchar(units))), units)
  paste0(substr(units, 1, nchar(units) - digits), ".", substring(units, nchar(units) - digits + 1))
}


# Decimals for a quantile: of small whole numbers (below 10, where whole numbers get no decimals by
# study.digit_steps), one that falls between two of them keeps one more: a median score of 2.5, not 3. Larger ones
# round as usual (an age quartile of 55.5 reads 56).
quantile_places <- function(value, digits, whole) {
  snapped <- round(value, 10)
  small <- abs(snapped) < hl_tokens()$study$digit_steps$min[1]
  if (whole && small && snapped != round(snapped)) digits + 1 else digits
}

#' Format numbers, percentages and intervals
#'
#' Fixed decimals, locale separators (`"en"` or `"de"`) and a true minus sign.
#'
#' @param value,share,estimate,low,high Numbers; `share` is a proportion (0.614 for 61.4 %).
#' @param digits Decimal places.
#' @param locale `"en"`, `"de"`, or `NULL` for the active setting.
#' @return A character string.
#' @examples
#' hl_format_number(1234.5, 1)
#' hl_format_number(-0.25, 2, locale = "de")
#' hl_format_percent(0.125, 1)
#' hl_format_interval(0.62, 0.41, 0.94)
#' @export
hl_format_number <- function(value, digits = 1, locale = NULL) {
  if (length(value) != 1) {
    stop(sprintf("hairline: hl_format_number formats one number; got %d (use vapply() for several)", length(value)),
         call. = FALSE)
  }
  symbols <- locale_symbols(locale)
  if (is.na(value)) return(missing_text)
  if (is.infinite(value)) return(paste0(if (value < 0) symbols$minus else "", "\u221e"))
  text <- fixed_text(abs(value), as.integer(digits))
  parts <- strsplit(text, ".", fixed = TRUE)[[1]]
  body <- group_thousands(parts[1], symbols$thousands)
  if (length(parts) > 1) body <- paste0(body, symbols$decimal, parts[2])
  is_negative <- value < 0 && grepl("[1-9]", text)
  paste0(if (is_negative) symbols$minus else "", body)
}

#' @rdname hl_format_number
#' @export
hl_format_percent <- function(share, digits = 1, locale = NULL) {
  if (is.na(share)) return(missing_text)
  paste0(hl_format_number(share * 100, digits, locale), locale_symbols(locale)$percent_space, "%")
}

#' @rdname hl_format_number
#' @export
hl_format_interval <- function(estimate, low, high, digits = 2, locale = NULL) {
  if (length(estimate) != 1 || length(low) != 1 || length(high) != 1) {
    stop("hairline: hl_format_interval formats one estimate with its interval; use mapply() for several",
         call. = FALSE)
  }
  parts <- vapply(c(estimate, low, high), hl_format_number, character(1), digits = digits, locale = locale)
  sprintf("%s [%s; %s]", parts[1], parts[2], parts[3])
}

is_whole <- function(values) length(values) > 0 && all(values == round(values))

# Decimals that give `size` (above zero) at least one unit in the last place.
places_for <- function(size) max(0, ceiling(-log10(size) - rounding_tolerance))

# Decimals that show `value` with two significant digits, at least `least` (a slope of 0.000407 is 0.00041, not
# 0.00), up to study.max_digits.
significant_places <- function(value, least = 2) {
  if (!is.finite(value) || value == 0) return(least)
  min(max(least, places_for(abs(value)) + 1), hl_tokens()$study$max_digits)
}

# Decimals for values and their quantiles: none for whole numbers (counts, scores), otherwise by the median magnitude
# (tokens study.digit_steps). More where the interquartile range (or, without one, the magnitude) would round away, so
# 1000.2 +/- 0.1 and 0.0004 keep their digits, up to study.max_digits. Means take one more for whole data.
auto_digits <- function(values) {
  values <- values[is.finite(values)]
  if (!length(values) || is_whole(values)) return(0)
  magnitude <- stats::median(abs(values))
  rules <- hl_tokens()$study
  steps <- rules$digit_steps
  digits <- steps$digits[nrow(steps)]
  for (index in rev(seq_len(nrow(steps)))) if (magnitude >= steps$min[index]) digits <- steps$digits[index]
  limits <- stats::quantile(values, c(0.25, 0.75), names = FALSE)
  spread <- limits[2] - limits[1]
  if (spread == 0) spread <- max(values) - min(values)
  for (size in c(spread, magnitude)) if (size > 0) digits <- max(digits, places_for(size))
  min(digits, rules$max_digits)
}
