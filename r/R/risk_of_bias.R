# Risk-of-bias summary, mirroring the Python risk_of_bias(): one 100 % bar per domain with the
# counts inside, an overall row below a rule, judgement colours and labels in the legend row.

judgement_levels <- c("low", "some", "high")
judgement_synonyms <- c(low = "low", `low risk` = "low", some = "some", `some concerns` = "some", unclear = "some",
                        moderate = "some", high = "high", `high risk` = "high", serious = "high", critical = "high")

judgement_of <- function(value, study, domain) {
  key <- tolower(trimws(value))
  if (!key %in% names(judgement_synonyms)) {
    stop(sprintf("hairline: risk of bias: judgement '%s' for %s, %s is not low, some concerns or high", value, study,
                 domain), call. = FALSE)
  }
  judgement_synonyms[[key]]
}

risk_of_bias_spec <- function(data, study, domain = NULL, judgement = NULL, domains = NULL, overall = "Overall") {
  if (!is.null(domains)) {
    check_columns(data, c(study, domains))
    check_labels(data, study, "risk of bias")
    table <- do.call(rbind, lapply(domains, function(name) {
      data.frame(study = data[[study]], domain = name, judgement = data[[name]])
    }))
  } else {
    if (is.null(domain) || is.null(judgement)) {
      stop(paste("hairline: risk of bias: name the domain and judgement columns of a long table, or the domain",
                 "columns of a wide one with domains = c(...)"), call. = FALSE)
    }
    check_columns(data, c(study, domain, judgement))
    check_labels(data, c(study, domain), "risk of bias")
    table <- data.frame(study = data[[study]], domain = data[[domain]], judgement = data[[judgement]])
  }
  keys <- combination_key(table$study, table$domain)
  repeated <- which(duplicated(keys))
  if (length(repeated)) {
    first <- repeated[1]
    stop(sprintf("hairline: risk of bias: %s has %d judgements for %s; give one per study and domain",
                 table$study[first], sum(keys == keys[first]), table$domain[first]), call. = FALSE)
  }
  table$level <- mapply(judgement_of, table$judgement, table$study, table$domain, USE.NAMES = FALSE)
  names <- unique(as.character(table$domain))
  counts <- lapply(names, function(name) {
    vapply(judgement_levels, function(level) sum(table$domain == name & table$level == level), integer(1),
           USE.NAMES = FALSE)
  })
  if (!is.null(overall)) {
    worst <- tapply(match(table$level, judgement_levels), factor(table$study, levels = unique(table$study)), max)
    names <- c(names, overall)
    counts[[length(counts) + 1]] <- vapply(seq_along(judgement_levels), function(index) sum(worst == index),
                                           integer(1))
  }
  list(domains = as.list(names), counts = counts, overall = if (is.null(overall)) NULL else length(names) - 1,
       colors = as.list(stats::setNames(unlist(hl_tokens()$sets$judgement[judgement_levels]), judgement_levels)))
}

risk_segments <- function(counts, left, right, top, height, colours, measure, style, gap, domain = "") {
  total <- sum(counts)
  shapes <- list()
  start <- left
  for (index in seq_along(counts)) {
    if (counts[index] == 0) next
    end <- start + (right - left) * counts[index] / total
    inner_left <- start + if (start > left) gap / 2 else 0
    inner_right <- end - if (end < right - 1e-9) gap / 2 else 0
    fill <- colours[[judgement_levels[index]]]
    label <- hl_tokens()$risk_of_bias$labels[[judgement_levels[index]]]
    segment <- list(kind = "polygon", role = judgement_levels[index], fill = fill,
                    points = rbind(c(inner_left, top), c(inner_right, top), c(inner_right, top + height),
                                   c(inner_left, top + height)))
    shapes[[length(shapes) + 1]] <- tagged_shape(segment, label, sprintf("%s, %s: %d", domain, label,
                                                                         as.integer(counts[index])))
    if (measure(as.character(counts[index]), "label") <= inner_right - inner_left - gap) {
      shapes[[length(shapes) + 1]] <- shape_text((inner_left + inner_right) / 2,
                                                 baseline_for(top + height / 2, style, "label"),
                                                 as.character(counts[index]), "label", contrast_text(fill, style),
                                                 "center")
    }
    start <- end
  }
  shapes
}

# Each domain's lines and the width of the label column: one line while the bars keep `min_plot`, wrapped into the
# room that leaves otherwise.
risk_domain_lines <- function(names, overall, box, measure, style, rules) {
  gap <- rules$label_gap * style$base
  least <- rules$min_plot * style$base
  labels <- max(vapply(names, measure, numeric(1), role = "label")) + gap
  if (box[3] - labels >= least) return(list(lines = as.list(names), labels = labels))
  weights <- lapply(seq_along(names), function(index) if (index == overall) 600 else NULL)
  lines <- lapply(seq_along(names), function(index) {
    fit_lines(names[index], box[3] - least - gap, measure, "risk of bias", "the domain", weight = weights[[index]])
  })
  widest <- max(vapply(seq_along(lines), function(index) {
    widest_line(lines[[index]], measure, weight = weights[[index]])
  }, numeric(1)))
  list(lines = lines, labels = widest + gap)
}

# Rows from the top; a wrapped domain makes its row as tall as its lines, its bar centred beside them.
risk_of_bias_drawing <- function(spec, box, measure, style) {
  rules <- hl_tokens()$risk_of_bias
  base <- style$base
  names <- unlist(spec$domains)
  overall <- if (is.null(spec$overall)) 0 else spec$overall + 1
  line <- line_height(style, "label")
  column <- risk_domain_lines(names, overall, box, measure, style, rules)
  extra <- if (overall > 0) rules$overall_gap * base else 0
  height <- min(rules$max_bar * base, (box[4] - extra - (length(names) - 1) * rules$row_gap * base) / length(names))
  shapes <- list()
  top <- box[2]
  for (index in seq_along(names)) {
    if (index == overall) {
      divider <- top - rules$row_gap * base / 2 + extra / 2
      rule <- rbind(c(box[1], divider), c(box[1] + box[3], divider))
      shapes[[length(shapes) + 1]] <- list(kind = "line", points = rule, color = style$neutral$axis,
                                           width = style$leader_width, part = "rule")
      top <- top + extra
    }
    lines <- column$lines[[index]]
    row <- if (length(lines) == 1) height else max(height, length(lines) * line)
    first <- top + row / 2 - (length(lines) - 1) * line / 2
    for (number in seq_along(lines)) {
      shapes[[length(shapes) + 1]] <- shape_text(box[1], baseline_for(first + (number - 1) * line, style, "label"),
                                                 lines[number], "label", style$neutral$ink, "left",
                                                 if (index == overall) 600 else NULL)
    }
    shapes <- c(shapes, risk_segments(as.numeric(unlist(spec$counts[[index]])), box[1] + column$labels,
                                      box[1] + box[3], top + (row - height) / 2, height, spec$colors, measure, style,
                                      rules$gap_pt, spec$domains[[index]]))
    top <- top + row + rules$row_gap * base
  }
  shapes
}

#' Risk-of-bias summary
#'
#' One 100 % bar per domain with the number of studies judged low, some
#' concerns or high inside, and an overall row (each study's worst judgement)
#' below a rule. Reads a long table (study, domain, judgement) or a wide one
#' with one column per domain.
#'
#' @param data A data frame.
#' @param study Study column.
#' @param domain,judgement Columns of a long table.
#' @param domains Domain columns of a wide table, in place of `domain` and `judgement`.
#' @param overall Name of the overall row; `NULL` leaves it out.
#' @param title,subtitle,caption Frame texts.
#' @return A ggplot with the hairline frame.
#' @examples
#' trials <- data.frame(study = c("Trial 1", "Trial 2"), Randomisation = c("Low", "Some concerns"),
#'                      Reporting = c("Low", "High"), check.names = FALSE)
#' hl_risk_of_bias(trials, "study", domains = c("Randomisation", "Reporting"))
#' @export
hl_risk_of_bias <- function(data, study, domain = NULL, judgement = NULL, domains = NULL, overall = "Overall",
                            title = NULL, subtitle = NULL, caption = NULL) {
  spec <- risk_of_bias_spec(data, study, domain, judgement, domains, overall)
  labels <- hl_tokens()$risk_of_bias$labels
  key <- lapply(judgement_levels, function(level) {
    list(kind = "square", colour = spec$colors[[level]], label = labels[[level]])
  })
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% "Risk of bias", subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE) + hl_legend(key)
  plot@meta$hairline_drawing <- function(box, measure, style) risk_of_bias_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot
}
