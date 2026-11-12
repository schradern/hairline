# summary = and stats =, mirroring the Python summaries.py: the measures distribution charts draw and write, named the
# same on every chart and in both languages. `summary` chooses the marks (the median, the mean as an open diamond, the
# IQR as a thick bar, the range as a thin line, the SD or 95% CI of the mean as a slim bar); `stats` writes the same
# measures as numbers.

summary_names <- c("median", "mean", "iqr", "range", "sd", "ci")
summary_centres <- c("median", "mean")
# Interval bars: each sits in the same place, so a chart draws one of them.
summary_bars <- c("iqr", "sd", "ci")
stat_names <- c(summary_names, "n")
# The centre an interval belongs to, where a chart draws one centre with one interval (dot plot, time series).
summary_paired <- c(iqr = "median", sd = "mean", ci = "mean")
summary_ci_level <- 0.95
summary_legend_kinds <- c(mean = "diamond", iqr = "bar", range = "thin", sd = "slim", ci = "slim")
summary_legend_words <- c(median = "median", mean = "mean", iqr = "iqr", range = "range", sd = "sd_bar", ci = "ci")

# Names as a character vector, each known and given once.
as_names <- function(value, chart, option, allowed) {
  names <- as.character(unlist(value))
  unknown <- setdiff(names, allowed)
  if (length(unknown)) {
    stop(sprintf("hairline: %s: unknown %s '%s'; use any of %s", chart, option, unknown[1],
                 paste(allowed, collapse = ", ")), call. = FALSE)
  }
  repeated <- unique(names[duplicated(names)])
  if (length(repeated)) {
    stop(sprintf("hairline: %s: %s names '%s' twice; name each once", chart, option, repeated[1]), call. = FALSE)
  }
  names
}

# The summary marks to draw: known names, each once, those the chart draws, and one interval bar at most.
check_summary <- function(summary, chart, allowed = summary_names, why = "") {
  names <- as_names(summary, chart, "summary", summary_names)
  refused <- setdiff(names, allowed)
  if (length(refused)) {
    stop(sprintf("hairline: %s: summary '%s' is not drawn here; %s draws %s%s", chart, refused[1], chart,
                 paste(allowed, collapse = ", "), if (nzchar(why)) paste0(". ", why) else ""), call. = FALSE)
  }
  bars <- names[names %in% summary_bars]
  if (length(bars) > 1) {
    stop(sprintf("hairline: %s: summary '%s' and '%s' would draw two bars in one place; give one of %s", chart,
                 bars[1], bars[2], paste(summary_bars, collapse = ", ")), call. = FALSE)
  }
  names
}

# One centre and at most one interval that belongs to it (the IQR to the median, the SD and CI to the mean; the range
# to either), for charts that draw a centre with its interval.
check_paired <- function(names, chart) {
  centres <- names[names %in% summary_centres]
  intervals <- names[!names %in% summary_centres]
  if (length(centres) != 1) {
    got <- if (length(centres)) paste0("'", centres, "'", collapse = ", ") else "none"
    stop(sprintf("hairline: %s: summary needs one centre, 'median' or 'mean'; got %s", chart, got), call. = FALSE)
  }
  if (length(intervals) > 1) {
    stop(sprintf("hairline: %s: summary draws one interval with its centre; got %s", chart,
                 paste0("'", intervals, "'", collapse = ", ")), call. = FALSE)
  }
  interval <- if (length(intervals)) intervals else NULL
  needed <- if (!is.null(interval) && interval %in% names(summary_paired)) summary_paired[[interval]]
  if (!is.null(needed) && needed != centres) {
    stop(sprintf("hairline: %s: '%s' goes with the %s; use summary = c(\"%s\", \"%s\")", chart, interval, needed,
                 needed, interval), call. = FALSE)
  }
  list(centre = centres, interval = interval)
}

# Every measure of `values`: n, range, quartiles (on the data's levels when `discrete`), mean, SD and the 95% CI of
# the mean (t distribution); SD and CI are NaN below two values.
summary_values <- function(values, discrete = FALSE) {
  values <- as.numeric(values)
  limits <- (if (discrete) level_quantiles else density_quantiles)(values, c(0, 0.25, 0.5, 0.75, 1))
  count <- length(values)
  centre <- mean(values)
  sd <- if (count > 1) stats::sd(values) else NaN
  half <- if (count > 1) stats::qt(1 - (1 - summary_ci_level) / 2, count - 1) * sd / sqrt(count) else NaN
  list(n = count, low = limits[1], q1 = limits[2], median = limits[3], q3 = limits[4], high = limits[5],
       mean = centre, sd = sd, ci_low = centre - half, ci_high = centre + half)
}

# An interval's ends from summary_values().
interval_of <- function(found, name) {
  switch(name, iqr = c(found$q1, found$q3), range = c(found$low, found$high),
         sd = c(found$mean - found$sd, found$mean + found$sd), c(found$ci_low, found$ci_high))
}

summary_formatter <- function(values, percent, digits, extra = 0) {
  scale <- if (percent) 100 else 1
  places <- (digits %||% auto_digits(values * scale)) + extra
  suffix <- if (percent) paste0(locale_symbols(NULL)$percent_space, "%") else ""
  function(value) paste0(hl_format_number(snap_noise(value * scale), places), suffix)
}

# A level as given: 12.5 mg stays 12.5 and 50 stays 50 (up to three decimals). On discrete data a rounded level would
# read as a dose nobody gave.
level_number <- function(value) {
  value <- snap_noise(value)
  hl_format_number(value, min(3, exact_places(value)))
}

# Formatters for quantiles and for means. Of whole numbers a mean takes one more decimal, and a quantile between two
# of them keeps one (a median of 2.5, not 3); on discrete data quantiles are levels as given.
measure_numbers <- function(every, percent, digits, discrete = FALSE) {
  whole <- is_whole(every) && !percent
  plain <- summary_formatter(every, percent, digits)
  mean_number <- summary_formatter(every, percent, digits, if (whole) 1 else 0)
  if (discrete && is.null(digits) && !percent) return(list(level_number, mean_number))
  halves <- whole && is.null(digits)
  list(function(value) if (quantile_places(value, 0, halves) > 0) mean_number(value) else plain(value), mean_number)
}

# The most frequent values with their shares: "25 (48%) · 50 (41%)".
levels_text <- function(values, number) {
  shown <- top_levels(values, hl_tokens()$spread$levels_shown)
  paste(paste0(vapply(shown$level, number, character(1)), " (",
               vapply(shown$share, hl_format_percent, character(1), digits = 0), ")"), collapse = " \u00b7 ")
}

stat_label <- function(name) if (name == "n") "n" else word(name)

stat_text <- function(name, found, numbers, values) {
  if (name == "n") return(hl_format_number(found$n, 0))
  if (name == "levels") return(levels_text(values, numbers[[1]]))
  if (name %in% c("sd", "ci") && !is.finite(found$sd)) return("\u2013")
  if (name == "median") return(numbers[[1]](found$median))
  if (name %in% c("mean", "sd")) return(numbers[[2]](found[[name]]))
  ends <- interval_of(found, name)
  shown <- if (name == "ci") numbers[[2]] else numbers[[1]]
  paste0(shown(ends[1]), "\u2013", shown(ends[2]))
}

# The measures as (label, value) pairs, drawn like a panel header's key numbers: "Median 12", "IQR 9-15".
stat_pairs <- function(values, names, numbers, discrete = FALSE) {
  values <- as.numeric(values)
  found <- summary_values(values, discrete)
  lapply(names, function(name) c(stat_label(name), stat_text(name, found, numbers, values)))
}

# Legend items naming each mark drawn, in the order given, in one colour (the groups keep theirs).
summary_legend <- function(names, median_kind, colour) {
  kinds <- c(summary_legend_kinds, median = median_kind)
  lapply(names, function(name) list(kind = kinds[[name]], colour = colour, label = word(summary_legend_words[[name]])))
}
