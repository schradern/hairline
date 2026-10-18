# Locale-aware number formatting shared with the Python package.

locale_symbols <- function(locale) {
  locales <- hl_tokens()$locales
  locale <- locale %||% (hairline_state$settings$locale %||% hl_tokens()$default_locale)
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

# `magnitude` (zero or more) with `digits` decimals, halves rounded up. Float noise below a billionth of the last digit
# does not decide (8.649999999999999 is 8.65), so every platform prints the same digits, as in the Python package.
fixed_text <- function(magnitude, digits) {
  scaled <- magnitude * 10^digits
  units <- sprintf("%.0f", floor(scaled + 0.5 + rounding_tolerance * max(1, scaled)))
  if (digits == 0) return(units)
  units <- paste0(strrep("0", max(0, digits + 1 - nchar(units))), units)
  paste0(substr(units, 1, nchar(units) - digits), ".", substring(units, nchar(units) - digits + 1))
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
  symbols <- locale_symbols(locale)
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
  paste0(hl_format_number(share * 100, digits, locale), locale_symbols(locale)$percent_space, "%")
}

#' @rdname hl_format_number
#' @export
hl_format_interval <- function(estimate, low, high, digits = 2, locale = NULL) {
  parts <- vapply(c(estimate, low, high), hl_format_number, character(1), digits = digits, locale = locale)
  sprintf("%s [%s; %s]", parts[1], parts[2], parts[3])
}

is_whole <- function(values) length(values) > 0 && all(values == round(values))

# Decimals for values and their quantiles: none for whole numbers (counts, scores), otherwise by the median magnitude
# (tokens study.digit_steps). Means take one more for whole data.
auto_digits <- function(values) {
  if (is_whole(values)) return(0)
  magnitude <- if (length(values)) stats::median(abs(values)) else 0
  steps <- hl_tokens()$study$digit_steps
  for (index in seq_len(nrow(steps))) if (magnitude >= steps$min[index]) return(steps$digits[index])
  steps$digits[nrow(steps)]
}
