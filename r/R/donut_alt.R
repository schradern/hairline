# The description of a donut or partition bars for its alt text: the total a donut's centre writes, then the largest
# and smallest part of the top level with their shares as the labels write them. Mirrors the Python package's
# charts/donut_alt.py.

# The words alt_extremes() writes for slices: both ends, one slice alone, every slice the same.
donut_slice_words <- c("slice_extremes", "slice_one", "slice_same")

# "Donut chart. Total: 700 patients. Largest: Home (59%); smallest: Died (3%)."; the total where the centre shows
# it, with the text under it; `kind` names partition bars, which show no total. As Python's donut_description().
donut_description <- function(ring, total, total_label, kind = "kind_donut") {
  findings <- if (!is.null(total)) {
    word("total_amount", total = if (is.null(total_label)) total else paste(total, total_label))
  }
  findings <- c(findings, alt_extremes(vapply(ring, `[[`, "", "name"), vapply(ring, `[[`, 0, "share"),
                                       vapply(ring, `[[`, "", "share_text"), donut_slice_words))
  alt_described(kind, paste(findings, collapse = " "))
}
