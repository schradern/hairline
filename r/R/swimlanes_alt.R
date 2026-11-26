# The description of swimlanes for their alt text: how many intervals in how many rows, from the earliest start to the
# latest end, and the longest interval as its tooltip names it. Mirrors the Python package's charts/swimlanes_alt.py.

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
