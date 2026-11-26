# The descriptions of a systematic review's figures for their alt text: a funnel plot's studies, pooled estimate and
# Egger's test as its header writes them, and a PRISMA flow's records at each stage. Mirrors the Python package's
# charts/review_alt.py.

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
