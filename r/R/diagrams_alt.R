# The descriptions of the flow and set diagrams for their alt text: a Sankey's total and its largest flow at each
# step, a chord diagram's largest exchange and the groups with the highest and lowest total, a Venn diagram's sets
# and how many are in all of them. Mirrors the Python package's charts/diagrams_alt.py.

# "ICU → Ward (40)": the names with the largest value, ties named together, and that value. As Python's largest().
alt_largest <- function(names, values, digits) {
  rounded <- round(values, alt_tie_digits)
  tied <- which(rounded == max(rounded))
  paste0(alt_named(names[tied]), " (", hl_format_number(values[tied[1]], digits), ")")
}

# Each step's flows from source to target, the colour groups added together, in order of first appearance: a list
# per step (0 first) of list(names, values). As Python's step_flows().
sankey_step_flows <- function(links) {
  columns <- sort(unique(vapply(links, function(link) as.integer(link$column), integer(1))))
  lapply(columns, function(column) {
    within <- Filter(function(link) link$column == column, links)
    names <- vapply(within, function(link) word("flow_name", source = link$source, target = link$target), "")
    values <- vapply(within, function(link) as.numeric(link$value), 0)
    keys <- unique(names)
    list(names = keys, values = vapply(keys, function(key) sum(values[names == key]), 0, USE.NAMES = FALSE))
  })
}

# "Sankey diagram. Total: 754. Largest flow per step: ICU → Ward (300); Ward → Home (280)." As Python's
# sankey_description().
sankey_description <- function(spec) {
  digits <- auto_digits(vapply(spec$links, function(link) as.numeric(link$value), 0))
  flows <- vapply(sankey_step_flows(spec$links), function(step) alt_largest(step$names, step$values, digits), "")
  total <- hl_format_number(sum(vapply(spec$nodes[[1]], `[[`, 0, "value")), digits)
  flows <- word(if (length(flows) == 1) "largest_flow" else "largest_flows", flows = paste(flows, collapse = "; "))
  findings <- c(word("total_amount", total = total), flows)
  alt_described("kind_sankey", paste(findings, collapse = " "))
}

# "Chord diagram. Largest exchange: ICU and Ward (80). Highest total: ICU (120); lowest: Rehab (20)." As Python's
# chord_description().
chord_description <- function(spec) {
  values <- vapply(spec$links, function(link) as.numeric(link$value), 0)
  pairs <- vapply(spec$links, function(link) word("pair_name", first = link$source, second = link$target), "")
  nodes <- alt_extremes(vapply(spec$nodes, `[[`, "", "name"), vapply(spec$nodes, `[[`, 0, "value"),
                        vapply(spec$nodes, `[[`, "", "value_text"), alt_centre_words, centre = word("node_total"))
  findings <- c(word("largest_exchange", pairs = alt_largest(pairs, values, auto_digits(values))), nodes)
  alt_described("kind_chord", paste(findings, collapse = " "))
}

# "Venn diagram. Sets: Diabetes (120), Obesity (90). In both: 40."; the last region holds every set. As Python's
# venn_description().
venn_description <- function(spec) {
  sets <- paste(vapply(spec$sets, function(entry) paste0(entry$name, " (", entry$value_text, ")"), ""),
                collapse = ", ")
  overlap <- word(if (length(spec$sets) == 2) "venn_both" else "venn_all",
                  value = spec$regions[[length(spec$regions)]]$value_text)
  alt_described("kind_venn", paste(word("venn_sets", sets = sets), overlap))
}
