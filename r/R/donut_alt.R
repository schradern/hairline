# The description of a donut for its alt text: the total its centre writes, then the largest and smallest slice of
# the inner ring with their shares as the labels write them. Mirrors the Python package's charts/donut_alt.py.

# The words alt_extremes() writes for slices: both ends, one slice alone, every slice the same.
donut_slice_words <- c("slice_extremes", "slice_one", "slice_same")

# "Donut chart. Total: 700 patients. Largest: Home (59%); smallest: Died (3%)."; the total where the centre shows
# it, with the text under it. As Python's donut_description().
donut_description <- function(ring, total, total_label) {
  findings <- if (!is.null(total)) {
    word("donut_total", total = if (is.null(total_label)) total else paste(total, total_label))
  }
  findings <- c(findings, alt_extremes(vapply(ring, `[[`, "", "name"), vapply(ring, `[[`, 0, "share"),
                                       vapply(ring, `[[`, "", "share_text"), donut_slice_words))
  alt_described("kind_donut", paste(findings, collapse = " "))
}
