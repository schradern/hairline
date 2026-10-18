# Venn diagram, mirroring the Python venn(): two or three sets, the count of every region, from named sets or
# membership columns.

venn_check_count <- function(names, proportional) {
  count <- length(names)
  listed <- paste(names, collapse = ", ")
  if (count > 3) {
    stop(sprintf("hairline: venn: %d sets given (%s); at most 3 fit — show the intersections as bars instead",
                 count, listed), call. = FALSE)
  }
  if (count < 2) {
    stop(sprintf("hairline: venn: %d set given (%s); a Venn diagram needs 2 or 3", count, listed), call. = FALSE)
  }
  if (proportional && count != 2) {
    stop(sprintf("hairline: venn: proportional areas need two sets; %d given", count), call. = FALSE)
  }
}

venn_column_codes <- function(data, columns) {
  check_columns(data, columns)
  codes <- numeric(nrow(data))
  for (bit in seq_along(columns)) {
    values <- data[[columns[bit]]]
    valid <- (is.logical(values) || is.numeric(values)) & !is.na(values) & values %in% c(0, 1)
    if (!all(valid)) {
      stop(sprintf("hairline: venn: column '%s' needs TRUE/FALSE or 0/1 values; found '%s'", columns[bit],
                   format(values[!valid][1])), call. = FALSE)
    }
    codes <- codes + as.numeric(values) * 2^(bit - 1)
  }
  codes
}

venn_member_codes <- function(sets) {
  members <- unique(unlist(sets, use.names = FALSE))
  codes <- numeric(length(members))
  for (bit in seq_along(sets)) codes <- codes + (members %in% sets[[bit]]) * 2^(bit - 1)
  codes
}

venn_spec <- function(data, columns = NULL, colors = NULL, proportional = FALSE) {
  if (is.data.frame(data)) {
    if (is.null(columns)) {
      stop("hairline: venn: name the membership columns, e.g. columns = c(\"diabetes\", \"obesity\")", call. = FALSE)
    }
    names <- humanise(columns)
    codes <- venn_column_codes(data, columns)
  } else {
    names <- as.character(names(data))
    codes <- venn_member_codes(data)
  }
  venn_check_count(names, proportional)
  palette <- colours_for(names, colors)
  sets <- lapply(seq_along(names), function(bit) {
    size <- sum(bitwAnd(codes, 2^(bit - 1)) > 0)
    list(name = names[bit], value = size, value_text = hl_format_number(size, 0), color = palette[[names[bit]]])
  })
  regions <- list()
  for (size in seq_along(names)) {
    for (members in utils::combn(seq_along(names), size, simplify = FALSE)) {
      count <- sum(codes == sum(2^(members - 1)))
      regions[[length(regions) + 1]] <- list(sets = members - 1, value = count,
                                             value_text = hl_format_number(count, 0))
    }
  }
  if (proportional && !all(vapply(sets, `[[`, numeric(1), "value") > 0)) {
    stop("hairline: venn: proportional areas need every set to have members", call. = FALSE)
  }
  list(sets = sets, regions = regions, proportional = proportional)
}

#' Venn diagram
#'
#' The overlap of two or three sets with the count of every region inside it
#' and each set's name and size outside. Circles are schematic (equal sizes);
#' with `proportional = TRUE`, two circles get areas proportional to their
#' sizes and overlap by the shared count. Four or more sets are refused: show
#' the intersections as bars instead.
#'
#' @param data A named list of member vectors, or a data frame with one row per member.
#' @param columns For a data frame, the membership columns (TRUE/FALSE or 0/1).
#' @param title,subtitle,caption Frame texts; the title defaults to the set names.
#' @param colors Named colours for this chart only; they override the colour set for the number of sets.
#' @param proportional Areas proportional to the counts (two sets only).
#' @return A ggplot with the hairline frame.
#' @export
hl_venn <- function(data, columns = NULL, title = NULL, subtitle = NULL, caption = NULL, colors = NULL,
                    proportional = FALSE) {
  spec <- venn_spec(data, columns, colors, proportional)
  label <- joined(if (is.data.frame(data)) columns else vapply(spec$sets, `[[`, character(1), "name"))
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% paste("Overlap of", label), subtitle = subtitle, caption = caption, x = NULL,
                  y = NULL) + theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) venn_drawing(spec, box, measure, style)
  plot
}
