# PRISMA 2020 flow diagram, mirroring the Python prisma(): main boxes outlined, exclusions to
# their right in the band colour, arrows, phases as rotated labels on brackets.

prisma_removals <- c(duplicates = "Duplicate records", automation = "Marked ineligible by automation tools",
                     other_removed = "Removed for other reasons")

prisma_counted <- function(label, value) sprintf("%s (n = %s)", label, hl_format_number(value, 0))

prisma_check <- function(counts) {
  number <- function(value) hl_format_number(value, 0)
  removed <- sum(unlist(counts[intersect(names(prisma_removals), names(counts))]))
  found <- counts$identified + (counts$registers %||% 0)
  checks <- list(list("screened", found - removed, sprintf("identified %s minus removed %s", number(found),
                                                           number(removed))))
  if (!is.null(counts$excluded)) {
    step <- if (!is.null(counts$sought)) "sought" else "assessed"
    checks[[length(checks) + 1]] <- list(step, counts$screened - counts$excluded,
                                         sprintf("screened %s minus excluded %s", number(counts$screened),
                                                 number(counts$excluded)))
  }
  if (!is.null(counts$sought) && !is.null(counts$assessed)) {
    lost <- counts$not_retrieved %||% 0
    checks[[length(checks) + 1]] <- list("assessed", counts$sought - lost,
                                         sprintf("sought %s minus not retrieved %s", number(counts$sought),
                                                 number(lost)))
  }
  if (!is.null(counts$assessed) && !is.null(counts$excluded_reasons)) {
    reasons <- sum(unlist(counts$excluded_reasons))
    checks[[length(checks) + 1]] <- list("included", counts$assessed - reasons,
                                         sprintf("assessed %s minus excluded %s", number(counts$assessed),
                                                 number(reasons)))
  }
  for (check in checks) {
    value <- counts[[check[[1]]]]
    if (!is.null(value) && value != check[[2]]) {
      warning(sprintf("hairline: prisma: %s %s is not %s", check[[1]], number(value), check[[3]]), call. = FALSE)
    }
  }
}

prisma_rows <- function(counts) {
  present <- intersect(names(prisma_removals), names(counts))
  removed <- vapply(present, function(key) prisma_counted(prisma_removals[[key]], counts[[key]]), character(1),
                    USE.NAMES = FALSE)
  found <- prisma_counted("Records identified from databases", counts$identified)
  if (!is.null(counts$registers)) {
    found <- c(found, prisma_counted("Records identified from registers", counts$registers))
  }
  rows <- list(list(main = found, exclusion = if (length(removed)) c("Records removed before screening:", removed)),
               list(main = prisma_counted("Records screened", counts$screened),
                    exclusion = if (!is.null(counts$excluded)) prisma_counted("Records excluded", counts$excluded)))
  if (!is.null(counts$sought)) {
    rows[[length(rows) + 1]] <- list(main = prisma_counted("Reports sought for retrieval", counts$sought),
                                     exclusion = if (!is.null(counts$not_retrieved)) {
                                       prisma_counted("Reports not retrieved", counts$not_retrieved)
                                     })
  }
  if (!is.null(counts$assessed)) {
    reasons <- unlist(counts$excluded_reasons)
    lines <- vapply(names(reasons), function(reason) prisma_counted(reason, reasons[[reason]]), character(1),
                    USE.NAMES = FALSE)
    rows[[length(rows) + 1]] <- list(main = prisma_counted("Reports assessed for eligibility", counts$assessed),
                                     exclusion = if (length(lines)) c("Reports excluded:", lines))
  }
  included <- prisma_counted("Studies included in review", counts$included)
  if (!is.null(counts$reports)) included <- c(included, prisma_counted("Reports of included studies", counts$reports))
  c(rows, list(list(main = included, exclusion = NULL)))
}

prisma_spec <- function(counts) {
  counts <- as.list(counts)
  missing <- setdiff(c("identified", "screened", "included"), names(counts))
  if (length(missing)) {
    stop(sprintf("hairline: prisma needs identified, screened and included; missing %s",
                 paste(missing, collapse = ", ")), call. = FALSE)
  }
  prisma_check(counts)
  rows <- prisma_rows(counts)
  list(rows = rows, phases = list(list("Identification", 0, 0), list("Screening", 1, length(rows) - 2),
                                  list("Included", length(rows) - 1, length(rows) - 1)))
}
