# The description of a dot plot for its alt text: the rows with the highest and lowest value, in the plot's digits;
# with `summary`, the centre it draws ("Highest median: ..."). Mirrors the Python package's charts/dotplot_alt.py.

# A row's value as its number writes it, with the percent sign the heading gives it where it is a share. As Python's
# dot_text().
dotplot_alt_text <- function(value, digits, percent) {
  if (isTRUE(percent)) alt_percent_text(value, digits) else hl_format_number(value, digits)
}

# "Dot plot. Highest: Medical (13.0%); lowest: Cardiac (6.0%)." over the rows as drawn, each named with its block
# where there are blocks ("2025 · Medical", the separator written here so it stays UTF-8 whatever locale the
# package was installed in); with a summary, its centre names the values. As Python's dotplot_description().
dotplot_description <- function(names, blocks, values, digits, percent, centre = NULL) {
  if (length(blocks)) names <- paste(blocks, "\u00b7", names)
  texts <- vapply(values, dotplot_alt_text, "", digits = digits, percent = percent)
  found <- if (is.null(centre)) alt_extremes(names, values, texts) else
    alt_extremes(names, values, texts, alt_centre_words, centre = word(paste0("centre_", centre)))
  alt_described("kind_dotplot", found)
}
