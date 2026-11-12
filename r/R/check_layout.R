# hl_check_layout(), mirroring the Python check_layout(): what a reader would see collide in a finished figure. The
# plot is drawn to SVG (svglite writes absolute positions in pt and each text's measured width), and the same rules
# are applied to what it holds.

#' Check a plot for collisions
#'
#' Draws the plot at its size and lists what a reader would see collide:
#' text over text, text off the figure, marks outside their plot. A figure
#' hairline drew should have none.
#'
#' @param plot A ggplot with [theme_hairline()].
#' @param size Size preset, as in [hl_save()] (`NULL` for the plot's own).
#' @param width_mm,height_mm Figure size in mm; override the preset.
#' @return A list of findings, each a list with `rule` (`"text_overlap"`, `"text_outside"` or `"mark_outside"`),
#'   the text or mark and its `box` (left, top, right, bottom in pt from the top-left corner); empty when there are
#'   none. Needs the 'svglite' package.
#' @examples
#' if (requireNamespace("svglite", quietly = TRUE)) {
#'   plot <- hl_bars(data.frame(unit = c("A", "B"), beds = c(12, 9)), "unit", "beds")
#'   length(hl_check_layout(plot))
#' }
#' @export
hl_check_layout <- function(plot, size = NULL, width_mm = NULL, height_mm = NULL) {
  if (!requireNamespace("svglite", quietly = TRUE)) {
    stop("hairline: hl_check_layout() needs the 'svglite' package", call. = FALSE)
  }
  size <- plot_size(plot, size)
  check_size_preset(size)
  plot <- plot_for_size(plot, size)
  size_mm <- fitted_size_mm(plot, figure_size_mm(size, width_mm, height_mm %||% plot@meta$hairline_height_mm))
  path <- tempfile(fileext = ".svg")
  on.exit(unlink(path))
  inches <- size_mm / 25.4
  draw_to_device(function() svglite::svglite(path, inches[1], inches[2], fix_text_size = TRUE), plot)
  layout_findings(readLines(path, warn = FALSE), inches * 72)
}

svg_attribute <- function(line, name) {
  found <- regmatches(line, regexec(sprintf("\\b%s='([^']*)'", name), line))[[1]]
  if (length(found) < 2) NA_character_ else found[2]
}

svg_number <- function(line, name) as.numeric(sub("px$", "", svg_attribute(line, name)))

svg_text_content <- function(line) {
  content <- sub("^.*<text[^>]*>(.*)</text>.*$", "\\1", line)
  for (entity in list(c("&lt;", "<"), c("&gt;", ">"), c("&quot;", "\""), c("&#39;", "'"), c("&amp;", "&"))) {
    content <- gsub(entity[1], entity[2], content, fixed = TRUE)
  }
  content
}

# Where a text's glyphs reach: from its baseline up by the cap height and down by the descender, along its width
# from its anchor. A text turned by -90 degrees reads upwards, its glyphs' tops to the left. As Python's ink_box().
svg_text_box <- function(line) {
  size <- as.numeric(sub(".*font-size: ([0-9.]+)px.*", "\\1", line))
  width <- svg_number(line, "textLength")
  anchor <- svg_attribute(line, "text-anchor")
  share <- switch(if (is.na(anchor)) "start" else anchor, middle = 0.5, end = 1, 0)
  metrics <- font_metrics()
  x <- svg_number(line, "x")
  y <- svg_number(line, "y")
  x <- if (is.na(x)) 0 else x
  y <- if (is.na(y)) 0 else y
  transform <- svg_attribute(line, "transform")
  if (!is.na(transform)) {
    moved <- as.numeric(regmatches(transform, regexec("translate\\(([-0-9.]+),([-0-9.]+)\\)", transform))[[1]][2:3])
    x <- x + moved[1]
    y <- y + moved[2]
  }
  content <- svg_text_content(line)
  style <- list(family = "Hairline Sans", size = size, weight = 400)
  lead <- text_width_pt(sub("^(\\s*).*$", "\\1", content), style)
  trail <- text_width_pt(sub("^.*?(\\s*)$", "\\1", content, perl = TRUE), style)
  if (!is.na(transform) && grepl("rotate\\(-90", transform)) {
    return(c(x - size * metrics$cap_height, y - width * (1 - share), x + size * metrics$descender, y + width * share))
  }
  start <- x - width * share
  # Leading and trailing spaces carry no ink (a key number's label run ends in one before its value).
  c(start + lead, y - size * metrics$cap_height, start + width - trail, y + size * metrics$descender)
}

svg_mark_box <- function(line) {
  if (grepl("^\\s*<circle", line)) {
    x <- svg_number(line, "cx")
    y <- svg_number(line, "cy")
    r <- svg_number(line, "r")
    return(c(x - r, y - r, x + r, y + r))
  }
  if (grepl("^\\s*<rect", line) && !grepl("width='100%'", line, fixed = TRUE)) {
    x <- svg_number(line, "x")
    y <- svg_number(line, "y")
    return(c(x, y, x + svg_number(line, "width"), y + svg_number(line, "height")))
  }
  points <- svg_attribute(line, "points")
  if (is.na(points)) return(NULL)
  values <- matrix(as.numeric(unlist(strsplit(trimws(points), "[ ,]+"))), ncol = 2, byrow = TRUE)
  c(min(values[, 1]), min(values[, 2]), max(values[, 1]), max(values[, 2]))
}

box_overlaps <- function(first, second, tolerance) {
  min(first[3], second[3]) - max(first[1], second[1]) > tolerance &&
    min(first[4], second[4]) - max(first[2], second[2]) > tolerance
}

box_reach <- function(box, outer, tolerance) {
  reach <- max(outer[1] - box[1], box[3] - outer[3], outer[2] - box[2], box[4] - outer[4], 0)
  if (reach > tolerance) reach else 0
}

# The texts (with boxes) and the marks drawn inside a panel's clip, each with that clip's rectangle.
svg_contents <- function(lines) {
  clips <- list()
  texts <- list()
  marks <- list()
  current <- NULL
  for (index in seq_along(lines)) {
    line <- lines[index]
    if (grepl("<clipPath id=", line, fixed = TRUE)) {
      clips[[svg_attribute(line, "id")]] <- svg_mark_box(lines[index + 1])
    } else if (grepl("^\\s*<g clip-path=", line)) {
      current <- clips[[sub(".*url\\(#([^)]*)\\).*", "\\1", line)]]
    } else if (grepl("^\\s*</g>", line)) {
      current <- NULL
    } else if (grepl("<text", line, fixed = TRUE)) {
      texts[[length(texts) + 1]] <- list(text = svg_text_content(line), box = svg_text_box(line))
    } else if (!is.null(current) && grepl("^\\s*<(circle|rect|polygon|polyline)", line)) {
      box <- svg_mark_box(line)
      kind <- sub("^\\s*<([a-z]+).*", "\\1", line)
      if (!is.null(box)) marks[[length(marks) + 1]] <- list(mark = kind, box = box, clip = current)
    }
  }
  list(texts = Filter(function(item) nzchar(trimws(item$text)), texts), marks = marks)
}

layout_findings <- function(lines, size_pt) {
  tolerance <- hl_tokens()$audit$tolerance
  contents <- svg_contents(lines)
  frame <- c(0, 0, size_pt)
  findings <- list()
  texts <- contents$texts
  for (index in seq_along(texts)) {
    if (box_reach(texts[[index]]$box, frame, tolerance) > 0) {
      findings[[length(findings) + 1]] <- list(rule = "text_outside", text = texts[[index]]$text,
                                               box = round(texts[[index]]$box, 2))
    }
    for (other in texts[-seq_len(index)]) {
      if (box_overlaps(texts[[index]]$box, other$box, tolerance)) {
        findings[[length(findings) + 1]] <- list(rule = "text_overlap", text = texts[[index]]$text, other = other$text,
                                                 box = round(texts[[index]]$box, 2), other_box = round(other$box, 2))
      }
    }
  }
  c(findings, mark_findings(contents$marks, frame, tolerance))
}

# Marks reaching past the clip of the panel they are drawn in; a clip as large as the figure is no panel.
mark_findings <- function(marks, frame, tolerance) {
  findings <- list()
  for (mark in marks) {
    if (isTRUE(all.equal(mark$clip, frame, tolerance = 1e-3))) next
    reach <- box_reach(mark$box, mark$clip, tolerance)
    if (reach > 0) {
      findings[[length(findings) + 1]] <- list(rule = "mark_outside", mark = mark$mark, reach = round(reach, 2),
                                               box = round(mark$box, 2))
    }
  }
  findings
}
