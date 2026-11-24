# Date columns in hl_profile(): read as dates, counted per month (quarter, year), drawn as a tile. As the Python
# package's date_values(), period_of() and date_tile().

# The column's dates without missing values (named by row); ISO date text is read as dates, anything else refused.
profile_dates <- function(study, name) {
  if (!name %in% names(study$data)) {
    stop(sprintf("hairline: profile: date column '%s' is not in the data; columns: %s", name,
                 paste(names(study$data), collapse = ", ")), call. = FALSE)
  }
  column <- study$data[[name]]
  rows <- which(!study_is_missing(column))
  present <- column[rows]
  if (inherits(present, c("Date", "POSIXt"))) return(stats::setNames(as.Date(present), rows))
  parsed <- if (is_text_column(present)) tryCatch(as.Date(study_iso_dates(present, name)), error = function(e) NULL)
  if (is.null(parsed)) {
    bad <- present[is.na(suppressWarnings(as.Date(as.character(present), optional = TRUE)))][1]
    stop(sprintf("hairline: profile: '%s' has '%s', which is not a date or ISO date text (2025-01-31)", name,
                 as.character(bad %||% present[1])), call. = FALSE)
  }
  stats::setNames(parsed, rows)
}

# Months while they stay few enough to read as bars, then quarters, then years.
profile_period <- function(first, last) {
  rules <- hl_tokens()$profile
  months <- (as.integer(format(last, "%Y")) - as.integer(format(first, "%Y"))) * 12 +
    as.integer(format(last, "%m")) - as.integer(format(first, "%m")) + 1
  if (months <= rules$month_bars) "M" else if (months / 3 <= rules$quarter_bars) "Q" else "Y"
}

# The first day of each date's period.
period_start <- function(dates, period) {
  year <- as.integer(format(dates, "%Y"))
  month <- as.integer(format(dates, "%m"))
  month <- switch(period, M = month, Q = (month - 1) %/% 3 * 3 + 1, Y = rep(1L, length(month)))
  as.Date(sprintf("%04d-%02d-01", year, month))
}

# A period as pandas prints it: 2022-01, 2022Q1, 2022.
period_text <- function(start, period) {
  switch(period, M = format(start, "%Y-%m"),
         Q = paste0(format(start, "%Y"), "Q", (as.integer(format(start, "%m")) - 1) %/% 3 + 1),
         Y = format(start, "%Y"))
}

# 'Jan 2023' in the figure's locale: short enough for a tile's header; the table keeps the exact dates.
profile_month_text <- function(day) {
  months <- hl_tokens()$locales[[hl_settings()$locale]]$months
  paste(months[[as.integer(format(day, "%m"))]], format(day, "%Y"))
}

# Bars of rows per month (quarter, year) over the whole period, split by group; the header names the first and last
# month.
profile_date_tile <- function(study, name, dates, groups, legend) {
  label <- study_label(study, name)
  column <- study$data[[name]]
  if (!length(dates)) return(profile_tile(list(), hl_panel_header(name = label, qualifier =
                                                                    profile_missing_note(column)), legend, list()))
  period <- profile_period(min(dates), max(dates))
  starts <- period_start(dates, period)
  steps <- c(M = "month", Q = "3 months", Y = "year")[[period]]
  every <- seq(min(starts), max(starts), by = steps)
  ends <- seq(every[1], by = steps, length.out = length(every) + 1)[-1]
  rows <- as.integer(names(dates))
  parts <- lapply(groups$strata, function(stratum) {
    counted <- table(factor(as.character(starts[stratum$mask[rows]]), levels = as.character(every)))
    list(stratum = stratum, values = as.numeric(counted))
  })
  tip <- function(spot, stratum, count) {
    paste0(label, " ", period_text(every[spot], period), profile_in_group(stratum), ": ",
           hl_format_number(count, 0))
  }
  stacked <- profile_stack(parts, groups$colours, data.frame(low = as.numeric(every), high = as.numeric(ends)), FALSE,
                           label, tip)
  rects <- stacked$rects
  rects$xmin <- as.Date(rects$xmin, origin = "1970-01-01")
  rects$xmax <- as.Date(rects$xmax, origin = "1970-01-01")
  stats <- c(From = paste(profile_month_text(min(dates)), "to", profile_month_text(max(dates))))
  qualifier <- profile_missing_note(column, paste("per", profile_periods[[period]]))
  header <- hl_panel_header(name = label, qualifier = qualifier, stats = stats)
  profile_tile(list(profile_rect_layer(rects, hl_settings()), profile_count_reach(stacked$totals), integer_scale(),
                    hairline_date_scale()), header, legend,
               stacked$targets)
}
