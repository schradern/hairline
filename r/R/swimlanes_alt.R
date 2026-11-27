# The descriptions of the time-of-day charts for their alt text: swimlanes' intervals and rows, from the earliest start
# to the latest end, and the longest interval as its tooltip names it; lanes' rows and their highest cell as its
# tooltip names it. Mirrors the Python package's charts/swimlanes_alt.py.

# "1 interval" or "12 intervals". As Python's counted().
swimlanes_counted <- function(count, one, many) {
  if (count == 1) word(one) else word(many, n = hl_format_number(count, 0))
}

# "Swimlane chart. 12 intervals in 5 rows, from 07:15 to 18:30. Longest: Hip · Theatre 2, 08:00–12:30."; each
# interval named as its tooltip names it, the first of equally long ones, and no longest for a single one. As
# Python's swimlanes_description().
swimlanes_description <- function(names, starts, ends, rows) {
  span <- word("swimlanes_span", intervals = swimlanes_counted(length(names), "intervals_one", "intervals_many"),
               rows = swimlanes_counted(rows, "rows_one", "rows_many"), start = clock(min(starts)),
               end = clock(max(ends)))
  if (length(names) == 1) return(alt_described("kind_swimlanes", span))
  lengths <- round(ends - starts, alt_tie_digits)
  index <- which(lengths == max(lengths))[1]
  longest <- word("swimlanes_longest", name = names[index], start = clock(starts[index]), end = clock(ends[index]))
  alt_described("kind_swimlanes", paste(span, longest))
}

# "Lane chart. 6 rows; highest at Bed 3, 10:00-10:30 (95%)." over the cells as their tooltips write them, the first of
# equally high ones reading row by row; a share of days in percent, else the mean count. As Python's
# lanes_description().
lanes_description <- function(matrix, bin, share) {
  every <- round(unlist(matrix, use.names = FALSE), alt_tie_digits)
  found <- which(every == max(every))[1] - 1
  bins <- length(matrix[[1]])
  name <- names(matrix)[found %/% bins + 1]
  amount <- matrix[[name]][found %% bins + 1]
  span <- hour_span(found %% bins, bin)
  value <- if (share) hl_format_percent(amount, 0) else hl_format_number(amount, 1)
  alt_described("kind_lanes", word("lanes_peak", rows = swimlanes_counted(length(matrix), "rows_one", "rows_many"),
                                   name = name, start = clock(span[1]), end = clock(span[2]), value = value))
}
