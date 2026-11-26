# A figure's description from its data, for its alt text: the kind of chart and what stands out, in the figure's
# locale ("Bar chart. Highest: ICU (727); lowest: Ward (495)."). Charts write it into plot@meta$hairline_description;
# figure_alt() puts it after the title and subtitle, so every file, the HTML figure and the host manifest carry it.
# Mirrors the Python package's alt_text.py: the same words, numbers and order in both packages.

# Values equal to this many decimals are a tie: shares divided in Python and R may differ in their last bits.
alt_tie_digits <- 9

# Names joined by commas, at most `alt_text.max_names` of them and how many more.
alt_named <- function(names) {
  most <- hl_tokens()$alt_text$max_names
  shown <- paste(utils::head(names, most), collapse = ", ")
  if (length(names) <= most) shown else word("more_names", names = shown, n = length(names) - most)
}

# A value already in percent (13.0) as the charts write it with its sign ("13.0%", "13,0 %" in de). As Python's
# percent_text().
alt_percent_text <- function(value, digits) {
  paste0(hl_format_number(value, digits), locale_symbols(NULL)$percent_space, "%")
}

# The words alt_extremes() writes: both ends, one value alone, every value the same.
alt_value_words <- c("extremes", "one_value", "all_same")
# The same for each group's centre ("Highest median: …"), its name given as the `centre` field.
alt_centre_words <- c("centre_extremes", "centre_one", "centre_same")

# The highest and lowest of `names`, `values` and `texts` (each value as written) in reading order, ties named
# together; one value on its own, or every value when they are all the same, in `words` with any further fields.
# Missing values are left out.
alt_extremes <- function(names, values, texts, words = alt_value_words, ...) {
  known <- is.finite(values)
  names <- names[known]
  texts <- texts[known]
  values <- round(values[known], alt_tie_digits)
  if (!length(values)) return("")
  if (length(values) == 1) return(word(words[2], name = names, value = texts, ...))
  high <- max(values)
  low <- min(values)
  if (high == low) return(word(words[3], value = texts[1], ...))
  highs <- which(values == high)
  lows <- which(values == low)
  word(words[1], high = alt_named(names[highs]), high_value = texts[highs[1]], low = alt_named(names[lows]),
       low_value = texts[lows[1]], ...)
}

# Where a grid (rows y, columns x) is highest and lowest, as its tooltips (grid_tips()) name the point: the first such
# point reading row by row.
alt_grid_extremes <- function(grid, tips, titles) {
  known <- is.finite(grid)
  high <- max(grid[known])
  low <- min(grid[known])
  point <- function(value) {
    found <- which(t(known & grid == value))[1]
    column <- (found - 1) %% ncol(grid) + 1
    row <- (found - 1) %/% ncol(grid) + 1
    list(at = word("grid_point", x_title = titles$x, x = tips$x[[column]], y_title = titles$y, y = tips$y[[row]]),
         text = tips$z[[row]][[column]])
  }
  if (round(high, alt_tie_digits) == round(low, alt_tie_digits)) {
    return(word("all_same", value = point(grid[known][1])$text))
  }
  highest <- point(high)
  lowest <- point(low)
  word("grid_extremes", high = highest$at, high_value = highest$text, low = lowest$at, low_value = lowest$text)
}

# The kind of chart (a `kind_*` word) and its findings, or the kind alone when nothing stands out.
alt_described <- function(kind, findings) {
  name <- word(kind)
  if (nzchar(findings)) word("described", kind = name, findings = findings) else paste0(name, ".")
}
