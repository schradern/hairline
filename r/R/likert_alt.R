# The description of a Likert chart for its alt text: the items with the highest and lowest share of ratings on the
# high side of the split, those levels named as the key names them. Mirrors the Python package's
# charts/likert_alt.py.

# The words alt_extremes() writes for the items: both ends, one item alone, every item the same; the levels as a
# field.
likert_item_words <- c("likert_extremes", "likert_one", "likert_same")

# The levels on the high side of the split, low to high. As Python's high_levels().
likert_high_levels <- function(bins) {
  sort(unlist(lapply(Filter(function(entry) entry$side == "right", bins), `[[`, "levels")))
}

# "Likert chart. Highest share at 4–5: Staffing (72%); lowest: Parking (18%)." over the rows as drawn, each named
# with its block where faceted ("2025 · Staffing", the separator written here so it stays UTF-8 whatever locale the
# package was installed in); `levels` names the high side as the key does. As Python's likert_description().
likert_description <- function(spec, levels, faceted) {
  high <- vapply(spec$bins, function(entry) entry$side == "right", logical(1))
  shares <- vapply(spec$rows, function(row) sum(row$shares[high]), 0)
  names <- vapply(spec$rows, `[[`, "", "name")
  if (faceted) names <- paste(vapply(spec$rows, `[[`, "", "section"), "\u00b7", names)
  alt_described("kind_likert", alt_extremes(names, shares, vapply(shares, alt_percent_text, "", digits = 0),
                                            likert_item_words, levels = levels))
}
