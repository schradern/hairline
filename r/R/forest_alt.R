# The description of a forest plot for its alt text: the pooled estimate with its interval where there is one, then the
# rows with the highest and lowest estimate, in the plot's digits. Mirrors the Python package's charts/forest_alt.py.

# "Forest plot. Pooled: 0.82 [0.70–0.96]. Highest: Lee 2021 (1.20); lowest: Smith 2019 (0.55)." As Python's
# forest_description().
forest_description <- function(rows, pooled, digits) {
  findings <- if (!is.null(pooled)) word("forest_pooled", label = pooled$label, effect = pooled$effect_text)
  estimates <- vapply(rows, function(row) as.numeric(row$estimate), numeric(1))
  findings <- c(findings, alt_extremes(vapply(rows, `[[`, "", "study"), estimates,
                                       vapply(estimates, hl_format_number, "", digits = digits)))
  alt_described("kind_forest", paste(findings[nzchar(findings)], collapse = " "))
}
