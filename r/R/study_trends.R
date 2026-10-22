# hl_over_time(): one measure over calendar time by group, mirroring the Python over_time().

iso_date_pattern <- "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
iso_zone_pattern <- "(Z|[+-][0-9]{2}:?[0-9]{2})$"
iso_time_pattern <- paste0("^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(:[0-9]{2}(\\.[0-9]+)?)?",
                           "(Z|[+-][0-9]{2}:?[0-9]{2})?$")

# Seconds east of UTC in an ISO zone suffix ("Z", "+01:00", "-0530"); 0 without one.
iso_offset <- function(text) {
  zone <- ifelse(grepl(iso_zone_pattern, text), sub(".*?(Z|[+-][0-9]{2}:?[0-9]{2})$", "\\1", text, perl = TRUE), "Z")
  digits <- gsub("[^0-9]", "", zone)
  hours <- suppressWarnings(as.numeric(substr(digits, 1, 2)))
  minutes <- suppressWarnings(as.numeric(substr(digits, 3, 4)))
  # Zones run from -12:00 to +14:00 in whole quarters of an hour at most; anything else is not a time zone.
  impossible <- zone != "Z" & (is.na(hours) | hours > 14 | is.na(minutes) | minutes >= 60)
  if (any(impossible)) {
    stop(sprintf("hairline: over_time: '%s' has the zone offset '%s', which is not a time zone", text[impossible][1],
                 zone[impossible][1]), call. = FALSE)
  }
  ifelse(zone == "Z", 0, ifelse(startsWith(zone, "-"), -1, 1) * (hours * 3600 + minutes * 60))
}

# ISO date text as dates, or as times (UTC) when any value carries a clock time; anything else is refused, as in
# the Python package.
study_iso_dates <- function(values, column) {
  text <- trimws(as.character(values))
  is_date <- grepl(iso_date_pattern, text)
  has_time <- grepl(iso_time_pattern, text)
  parsed <- if (any(has_time)) {
    offset <- ifelse(has_time, iso_offset(text), 0)
    clock <- ifelse(is_date, paste(text, "00:00:00"), sub("T", " ", sub(iso_zone_pattern, "", text), fixed = TRUE))
    clock <- ifelse(grepl("^.{16}$", clock), paste0(clock, ":00"), clock)
    as.POSIXct(clock, tz = "UTC", format = "%Y-%m-%d %H:%M:%OS") - offset
  } else {
    as.Date(text, format = "%Y-%m-%d")
  }
  bad <- is.na(parsed) | !(is_date | has_time)
  if (any(bad)) {
    stop(sprintf("hairline: over_time: '%s' has '%s', which is not an ISO date (2025-01-31)", column,
                 text[bad][1]), call. = FALSE)
  }
  parsed
}

study_dated_rows <- function(study, date, value) {
  if (!date %in% names(study$data)) {
    stop(sprintf("hairline: over_time: date column '%s' is not in the data; columns: %s", date,
                 paste(names(study$data), collapse = ", ")), call. = FALSE)
  }
  data <- study_present_rows(study, value)
  data <- data[!study_is_missing(data[[date]]), , drop = FALSE]
  if (is.character(data[[date]]) || is.factor(data[[date]])) data[[date]] <- study_iso_dates(data[[date]], date)
  data[[value]] <- study_as_number(data[[value]])
  data
}

#' One measure over time by group
#'
#' Small multiples per group with the raw values and a trailing mean; the
#' table gives n, mean (SD) and median (IQR) over the whole period. ISO date
#' text (2025-01-31) is read as dates.
#'
#' @param study A study from [hl_study()].
#' @param date Column with dates (or numbers on a time axis).
#' @param value Numeric column to follow.
#' @param window Observations in the trailing mean.
#' @return A `hairline_result`.
#' @examples
#' set.seed(1)
#' visits <- data.frame(day = 1:60, lactate = round(2 + sin(1:60 / 8) + stats::rnorm(60, 0, 0.3), 1))
#' study <- hl_study(visits, units = c(day = "days", lactate = "mmol/l"))
#' hl_over_time(study, "day", "lactate", window = 7)$text
#' @export
hl_over_time <- function(study, date, value, window = 7) {
  study_require(study, c(study$roles$group, value), "over_time")
  if (!identical(study$types[[value]], "numeric")) {
    stop(sprintf("hairline: over_time: '%s' is not numeric", value), call. = FALSE)
  }
  data <- study_dated_rows(study, date, value)
  every <- study_numbers(data[[value]])
  digits <- study_digits(every)
  whole <- is_whole(every)
  parts <- if (is.null(study$roles$group)) study_subsets(study) else study_group_parts(study)
  key <- study_group_key(study)
  found <- stats::setNames(lapply(parts, function(part) {
    sample <- study_numbers(data[[value]][data[[key]] == part$name])
    summary_numbers(sample, c("mean_sd", "median_iqr"), nrow(part$rows) - length(sample))
  }), study_part_names(parts))
  names <- Filter(function(name) found[[name]]$n > 0, names(found))
  study_require_values(names, value, "over_time")
  rows <- lapply(names, function(name) {
    c(name, hl_format_number(found[[name]]$n, 0), summary_text(found[[name]], "mean_sd", digits, whole),
      summary_text(found[[name]], "median_iqr", digits, whole))
  })
  means <- vapply(found[names], function(group) study_mean_text(group$mean, digits, whole), character(1),
                  USE.NAMES = FALSE)
  unit <- study_measure(study, value)
  figure <- study_figure("over_time", names, "groups", function() {
    drawn <- hl_timeseries(data[order(data[[date]]), , drop = FALSE], date, value,
                           by = if (!is.null(study$roles$group)) key, order = names, window = window,
                           title = paste(study_label(study, value), "over time"))
    if (is.null(unit)) drawn else drawn + ggplot2::labs(y = unit)
  })
  table <- as.data.frame(do.call(rbind, rows), stringsAsFactors = FALSE)
  names(table) <- c("Group", "n", "mean (SD)", "median (IQR)")
  counted <- study_counted_rows(study, c(list(variable = value), study_group_role(study), list(date = date)))
  text <- paste0(sprintf("%s, mean over the period: %s.", study_label_unit(study, value),
                         listed_text(paste(names, means))), left_out_text(counted, c("row", "rows")))
  study_result(figure, table, stats::setNames(as.list(means), names), text, list(rows = counted, groups = found))
}
