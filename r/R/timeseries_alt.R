# The description of a time series for its alt text: where each series' line starts, ends and is highest. The line is
# the one the chart emphasises, the rolling mean (or with `summary =` the centre), not the raw values under it.
# Mirrors the Python package's charts/timeseries_alt.py.

# The drawn line of one series (rows of prepared_series(), in order of x) as `x` and `value`, without its missing
# points. As Python's series_line().
timeseries_alt_line <- function(rows, marks) {
  if (is.null(marks)) {
    line <- data.frame(x = rows$.x, value = rows$.mean)
  } else {
    found <- if (any(!is.na(rows$.y))) summary_series(rows, marks)
    line <- if (is.null(found)) data.frame(x = rows$.x[0], value = numeric()) else
      data.frame(x = found$.x, value = found$.centre)
  }
  line[!is.na(line$x) & is.finite(line$value), , drop = FALSE]
}

# X values as the tooltips write them: ISO dates, with the clock time when any point has one; numbers by the shared
# digits rule. As Python's moment_texts().
timeseries_alt_moments <- function(values) {
  if (inherits(values, "Date")) return(format(values, "%Y-%m-%d"))
  if (inherits(values, "POSIXct")) return(datetime_texts(as.numeric(values), attr(values, "tzone")))
  interactive_numbers(as.numeric(values), FALSE)
}

# One series: from its first value to its last, and where it is highest (the earliest, on a tie): at its start, its
# end, or a point between, named. As Python's course().
timeseries_alt_course <- function(name, xs, values, line) {
  suffix <- if (nzchar(name)) "" else "_alone"
  if (nrow(line) == 1) return(word(paste0("line_point", suffix), name = name, value = values[1], when = xs[1]))
  peak <- which.max(round(line$value, alt_tie_digits))
  last <- nrow(line)
  highest <- if (peak == 1) word("peak_start") else if (peak == last) word("peak_end") else
    word("peak_at", peak = values[peak], when = xs[peak])
  word(paste0("line_course", suffix), name = name, first = values[1], start = xs[1], last = values[last],
       end = xs[last], highest = highest)
}

# "Line chart. ICU: from 41 (2025-01-01) to 52 (2025-12-01), highest 55 (2025-08-01). …" for the first
# `alt_text.max_series` series with points, then how many more; the values share one digits rule. As Python's
# timeseries_description().
timeseries_description <- function(names, lines, percent) {
  shown <- vapply(lines, nrow, integer(1)) > 0
  names <- names[shown]
  lines <- lines[shown]
  if (!length(lines)) return(alt_described("kind_lines", ""))
  xs <- timeseries_alt_moments(do.call(c, lapply(lines, `[[`, "x")))
  values <- interactive_numbers(unlist(lapply(lines, `[[`, "value")), percent)
  most <- hl_tokens()$alt_text$max_series
  ends <- cumsum(vapply(lines, nrow, integer(1)))
  starts <- ends - vapply(lines, nrow, integer(1)) + 1
  described <- seq_len(min(most, length(lines)))
  sentences <- vapply(described, function(index) {
    at <- starts[index]:ends[index]
    timeseries_alt_course(names[index], xs[at], values[at], lines[[index]])
  }, character(1))
  left <- length(lines) - length(described)
  if (left == 1) sentences <- c(sentences, word("more_series_one"))
  if (left > 1) sentences <- c(sentences, word("more_series_many", n = left))
  alt_described("kind_lines", paste(sentences, collapse = " "))
}
