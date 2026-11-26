# The descriptions of a systematic review's figures for their alt text: a funnel plot's studies, pooled estimate and
# Egger's test as its header writes them, a PRISMA flow's records at each stage, and a risk-of-bias summary's overall
# judgements and the domain most often judged high. Mirrors the Python package's charts/review_alt.py.

# "Funnel plot. 12 studies; pooled estimate 0.82, Egger's test p = 0.210." As Python's funnel_description().
funnel_description <- function(studies, estimate, egger) {
  alt_described("kind_funnel", word("funnel_found", n = hl_format_number(studies, 0), estimate = estimate,
                                    egger = egger))
}

# The stages the description names, each with the counts it adds together.
prisma_stages <- list(prisma_identified = c("identified", "registers"), prisma_screened = "screened",
                      prisma_assessed = "assessed", prisma_included = "included")

# "PRISMA flow diagram. 1,200 records identified, 800 screened, 40 reports assessed, 12 studies included."; the
# records from registers count with those from databases, and stages left out of `counts` are left out here. As
# Python's prisma_description().
prisma_description <- function(counts) {
  counts <- as.list(counts)
  shown <- Filter(function(keys) keys[1] %in% names(counts), prisma_stages)
  stages <- vapply(names(shown), function(name) {
    keys <- intersect(shown[[name]], names(counts))
    word(name, n = hl_format_number(sum(unlist(counts[keys])), 0))
  }, "")
  alt_described("kind_prisma", word("prisma_flow", stages = paste(stages, collapse = ", ")))
}

# "Risk-of-bias summary. Overall: 4 low, 3 some concerns, 1 high. Most often high: Randomisation (3)."; the overall
# row where the chart draws one, then the domains with the most high judgements where any has one. As Python's
# risk_of_bias_description().
risk_of_bias_description <- function(spec) {
  domains <- unlist(spec$domains)
  counts_text <- function(index) {
    counts <- vapply(spec$counts[[index]], hl_format_number, "", digits = 0)
    word("rob_counts", label = domains[index], low = counts[1], some = counts[2], high = counts[3])
  }
  overall <- if (!is.null(spec$overall)) spec$overall + 1
  findings <- if (!is.null(overall)) counts_text(overall)
  others <- setdiff(seq_along(domains), overall)
  highs <- vapply(spec$counts[others], function(counts) as.numeric(counts[3]), 0)
  if (max(highs) > 0) {
    findings <- c(findings, word("rob_most_high", domains = alt_named(domains[others][highs == max(highs)]),
                                 n = hl_format_number(max(highs), 0)))
  }
  alt_described("kind_risk_of_bias", paste(findings, collapse = " "))
}
