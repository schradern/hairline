# The description of a bar chart for its alt text: its highest and lowest bars, as their labels write them. Mirrors
# the Python package's charts/bars_alt.py.

# Between the parts of a bar's name: its panel, its category and its group ("Surgery / ICU / 2025").
bar_name_parts <- " / "

# A bar's name from its parts, each once (a facet by the groups names them once).
bar_alt_name <- function(parts) paste(unique(parts), collapse = bar_name_parts)

# The sum of the values; missing when none has one.
bar_alt_amount <- function(values) {
  known <- values[!is.na(values)]
  if (length(known)) sum(known) else NA_real_
}

# Each bar of a panel as a row of `name`, `value` and `text` (the value as written), in reading order: category,
# then group. A stack without shares is one bar, its total, as its label above it.
bar_alt_entries <- function(parts, category, by, groups, options, faceted) {
  table <- parts$table
  numbers <- bar_numbers(table, category, options$stacked)
  write <- function(amount, percent) {
    if (is.na(amount)) return("")
    if (percent) hl_format_percent(amount, digits = 0) else format_compact(amount, numbers$digits, numbers$unit)
  }
  labels <- as.character(table[[category]])
  members <- if (is.null(by)) NULL else as.character(table[[by]])
  prefix <- if (faceted) as.character(parts$facet) else character()
  entries <- list()
  add <- function(name, amount, percent) {
    entries[[length(entries) + 1]] <<- list(name = bar_alt_name(name), value = amount, text = write(amount, percent))
  }
  for (name in parts$names) {
    rows <- labels %in% name
    if (options$stacked && !options$divide) {
      add(c(prefix, name), bar_alt_amount(table$.value[rows]), FALSE)
      next
    }
    total <- bar_alt_amount(table$.value[rows])
    for (group in groups) {
      cell <- if (is.null(by)) rows else rows & members %in% group
      if (!any(cell)) next
      add(c(prefix, name, if (!is.null(by)) group), bar_alt_amount(table$.value[cell]) /
            (if (options$divide) total else 1), options$percent)
    }
  }
  entries
}

# "Bar chart. Highest: …; lowest: …." over every panel. As Python's bars_description().
bars_description <- function(panels, category, by, groups, options, faceted) {
  entries <- unlist(lapply(panels, bar_alt_entries, category = category, by = by, groups = groups, options = options,
                           faceted = faceted), recursive = FALSE)
  values <- vapply(entries, function(entry) as.numeric(entry$value), numeric(1))
  alt_described("kind_bars", alt_extremes(vapply(entries, `[[`, "", "name"), values,
                                          vapply(entries, `[[`, "", "text")))
}
