# Interactive HTML, mirroring the Python interactive module: the static SVG plus targets for
# tooltips and series highlighting, drawn by the script shared with the Python package. Targets in pt from the top-left.

# Data layers that stay out of interactive targets (fit lines, density outlines, jittered points).
static_layer <- function(layer) {
  layer$hairline_static <- TRUE
  layer
}

interactive_numbers <- function(values, percent) {
  if (percent) {
    digits <- auto_digits(values * 100)
    return(vapply(values, function(value) hl_format_percent(round(value, 10), digits), character(1)))
  }
  digits <- auto_digits(values)
  vapply(values, function(value) hl_format_number(round(value, 10), digits), character(1))
}

is_percent_scale <- function(scale) isTRUE(scale$hairline$percent)

# X (or y) values as text: ISO dates on a date scale, category names on a discrete scale, else numbers.
axis_texts <- function(params, scale, values) {
  if (scale$is_discrete()) {
    labels <- params$get_labels()
    return(vapply(round(values), function(position) {
      if (position >= 1 && position <= length(labels)) as.character(labels[[position]]) else ""
    }, character(1)))
  }
  if (inherits(scale, "ScaleContinuousDate")) return(format(as.Date(values, origin = "1970-01-01"), "%Y-%m-%d"))
  interactive_numbers(values, is_percent_scale(scale))
}

colour_hex <- function(colour) tolower(substr(grDevices::rgb(t(grDevices::col2rgb(colour)), maxColorValue = 255), 1, 7))

series_named <- function(colour, parts, index) {
  items <- Filter(function(item) !is.null(item$colour) && colour_hex(item$colour) == colour_hex(colour), parts$legend)
  if (length(items)) return(items[[1]]$label)
  header <- panel_header_for(parts, index)
  header$name %||% parts$title %||% ""
}

panel_position <- function(built) {
  layout <- built@layout$layout
  ordered <- as.character(layout$PANEL[order(layout$ROW, layout$COL)])
  function(panel) match(as.character(panel), ordered)
}

data_to_pt <- function(box, params) {
  x_range <- params$x$continuous_range
  y_range <- params$y$continuous_range
  function(x, y) {
    cbind(box[1] + (x - x_range[1]) / diff(x_range) * box[3],
          box[2] + box[4] - (y - y_range[1]) / diff(y_range) * box[4])
  }
}

step_points <- function(x, y) {
  if (length(x) < 2) return(cbind(x, y))
  rows <- list(c(x[1], y[1]))
  for (index in 2:length(x)) rows <- c(rows, list(c(x[index], y[index - 1]), c(x[index], y[index])))
  do.call(rbind, rows)
}

panel_context <- function(parts, plan, panel) {
  built <- parts$built
  layout <- built@layout$layout
  index <- panel_position(built)(panel)
  row <- layout[as.character(layout$PANEL) == as.character(panel), , drop = FALSE]
  box <- fitted_box(plan$layout$panels[[index]], parts$aspect)
  params <- built@layout$panel_params[[as.integer(panel)]]
  list(index = index, box = box, params = params, to_pt = data_to_pt(box, params),
       x_scale = built@layout$panel_scales_x[[row$SCALE_X[1]]], y_scale = built@layout$panel_scales_y[[row$SCALE_Y[1]]])
}

line_targets <- function(data, geom, parts, plan, scaled) {
  lapply(split(data, list(data$PANEL, data$group), drop = TRUE), function(rows) {
    context <- panel_context(parts, plan, rows$PANEL[1])
    path <- if (geom == "GeomStep") step_points(rows$x, rows$y) else cbind(rows$x, rows$y)
    name <- series_named(rows$colour[1], parts, context$index)
    xs <- axis_texts(context$params$x, context$x_scale, rows$x)
    ys <- interactive_numbers(rows$y, is_percent_scale(context$y_scale))
    at <- context$to_pt(rows$x, rows$y)
    width <- rows$linewidth[1] * ggplot2::.pt * 0.75 * if (scaled) line_scale(context$box[3]) else 1
    list(name = name, color = colour_hex(rows$colour[1]),
         marks = list(list(line = context$to_pt(path[, 1], path[, 2]), width = width)),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = at[index, ], text = paste0(name, ": ", xs[index], ", ", ys[index]))
         }))
  })
}

point_targets <- function(data, parts, plan) {
  data <- data[data$shape %in% c(16, 19), , drop = FALSE]
  if (!nrow(data)) return(list())
  lapply(split(data, list(data$PANEL, data$colour), drop = TRUE), function(rows) {
    context <- panel_context(parts, plan, rows$PANEL[1])
    name <- series_named(rows$colour[1], parts, context$index)
    at <- context$to_pt(rows$x, rows$y)
    xs <- axis_texts(context$params$x, context$x_scale, rows$x)
    ys <- interactive_numbers(rows$y, is_percent_scale(context$y_scale))
    radius <- rows$size[1] * ggplot2::.pt * 0.75 / 2
    list(name = name, color = colour_hex(rows$colour[1]),
         marks = lapply(seq_len(nrow(rows)), function(index) list(dot = at[index, ], r = radius)),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = at[index, ], text = paste0(name, ": ", xs[index], ", ", ys[index]))
         }))
  })
}

bar_targets <- function(data, parts, plan) {
  lapply(split(data, list(data$PANEL, data$fill), drop = TRUE), function(rows) {
    context <- panel_context(parts, plan, rows$PANEL[1])
    horizontal <- isTRUE(rows$flipped_aes[1])
    name <- series_named(rows$fill[1], parts, context$index)
    top_left <- context$to_pt(rows$xmin, rows$ymax)
    bottom_right <- context$to_pt(rows$xmax, rows$ymin)
    values <- if (horizontal) rows$xmax - rows$xmin else rows$ymax - rows$ymin
    texts <- interactive_numbers(values, is_percent_scale(if (horizontal) context$x_scale else context$y_scale))
    categories <- if (horizontal) axis_texts(context$params$y, context$y_scale, (rows$ymin + rows$ymax) / 2) else
      axis_texts(context$params$x, context$x_scale, (rows$xmin + rows$xmax) / 2)
    widths <- bottom_right[, 1] - top_left[, 1]
    list(name = name, color = colour_hex(rows$fill[1]),
         marks = lapply(seq_len(nrow(rows)), function(index) {
           list(rect = c(top_left[index, ], widths[index], bottom_right[index, 2] - top_left[index, 2]))
         }),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = c(top_left[index, 1] + widths[index] / 2, top_left[index, 2]),
                text = paste0(name, ": ", categories[index], ", ", texts[index]))
         }))
  })
}

layer_targets <- function(parts, plan, index) {
  layer <- parts$built@plot@layers[[index]]
  data <- parts$built@data[[index]]
  skipped <- isTRUE(layer$hairline_static) || isTRUE(layer$hairline_fixed) || isTRUE(layer$hairline_secondary)
  if (skipped || !nrow(data)) return(list())
  geom <- class(layer$geom)[1]
  if (geom %in% c("GeomLine", "GeomPath", "GeomStep")) return(unname(line_targets(data, geom, parts, plan, TRUE)))
  if (geom == "GeomPoint") return(unname(point_targets(data, parts, plan)))
  if (geom == "GeomCol") return(unname(bar_targets(data, parts, plan)))
  list()
}

drawn_targets <- function(shapes) {
  found <- list()
  for (shape in shapes) {
    if (is.null(shape$series)) next
    entry <- found[[shape$series]] %||% list(name = shape$series, color = shape$fill %||% shape$color,
                                             marks = list(), tips = list())
    if (shape$kind == "polygon") {
      entry$marks[[length(entry$marks) + 1]] <- list(polygon = shape_points(shape), alpha = shape$alpha %||% 1)
    } else if (shape$kind == "line") {
      entry$marks[[length(entry$marks) + 1]] <- list(line = shape_points(shape), width = shape$width)
    }
    if (!is.null(shape$tip)) entry$tips[[length(entry$tips) + 1]] <- list(at = shape$tip_at, text = shape$tip)
    found[[shape$series]] <- entry
  }
  unname(found)
}

merge_targets <- function(series) {
  merged <- list()
  for (entry in series) {
    if (is.null(merged[[entry$name]])) {
      merged[[entry$name]] <- entry
    } else {
      merged[[entry$name]]$marks <- c(merged[[entry$name]]$marks, entry$marks)
      merged[[entry$name]]$tips <- c(merged[[entry$name]]$tips, entry$tips)
    }
  }
  unname(merged)
}

legend_targets <- function(parts, plan) {
  centers <- plan$layout$legend_row_centers
  line <- role_size(parts$settings, "label") * (1 + hl_tokens()$type$line_gap)
  lapply(Filter(function(entry) entry$row + 1 <= length(centers), plan$placed), function(entry) {
    list(name = entry$label, box = c(entry$x, centers[entry$row + 1] - line / 2, entry$right - entry$x, line))
  })
}

plot_targets <- function(parts, plan) {
  series <- unlist(lapply(seq_along(parts$built@data), function(index) layer_targets(parts, plan, index)),
                   recursive = FALSE)
  settings <- parts$settings
  rules <- hl_tokens()$interactive
  style <- list(ink = settings$neutral$ink, surface = settings$neutral$surface, axis = settings$neutral$axis,
                font = settings$font, size = role_size(settings, "label"), veil = rules$veil, hit = rules$hit_pt)
  targets <- list(version = 1, width = plan$size[1], height = plan$size[2], style = style,
                  panels = lapply(seq_along(parts$panels), function(index) {
                    fitted_box(plan$layout$panels[[index]], parts$aspect)
                  }),
                  series = merge_targets(c(series, drawn_targets(plan$shapes))), legend = legend_targets(parts, plan))
  rapply(targets, function(value) round(value, 2), classes = "numeric", how = "replace")
}

interactive_targets <- function(plot, size = "onehalf", width_mm = NULL, height_mm = NULL) {
  framed <- frame_plan(plot, size, width_mm, height_mm, "html export")
  plot_targets(framed$parts, framed$plan)
}

interactive_asset <- function(name) {
  paste(readLines(system.file("interactive", name, package = "hairline"), encoding = "UTF-8", warn = FALSE),
        collapse = "\n")
}

font_faces <- function(family) {
  weights <- c(Regular = 400, Medium = 500, SemiBold = 600)
  paste0(vapply(hl_tokens()$interactive$fonts, function(file) {
    path <- system.file("fonts", file, package = "hairline")
    weight <- weights[[sub("\\..*$", "", sub("^[^-]*-", "", file))]]
    data <- jsonlite::base64_enc(readBin(path, "raw", file.info(path)$size))
    sprintf("@font-face{font-family:'%s';font-weight:%d;src:url(data:font/ttf;base64,%s) format('truetype')}",
            family, weight, gsub("\n", "", data))
  }, character(1)), collapse = "")
}

# One self-contained <figure>: static SVG, overlay, tooltip box, targets and script (embeddable as is).
figure_html <- function(svg, targets, family, alt = "") {
  body <- substring(svg, regexpr("<svg", svg, fixed = TRUE))
  style <- targets$style
  variables <- sprintf("--hl-ink:%s;--hl-surface:%s;--hl-axis:%s;--hl-font:'%s'", style$ink, style$surface,
                       style$axis, style$font)
  data <- gsub("</", "<\\/", jsonlite::toJSON(targets, auto_unbox = TRUE, digits = NA), fixed = TRUE)
  label <- gsub("<", "&lt;", gsub('"', "&quot;", gsub("&", "&amp;", alt, fixed = TRUE), fixed = TRUE), fixed = TRUE)
  paste0('<figure class="hairline-figure" style="', variables, '" aria-label="', label, '"><style>',
         font_faces(family),
         interactive_asset("hairline.css"), "</style>", body, '<svg class="hairline-overlay" viewBox="0 0 ',
         targets$width, " ", targets$height, '" xmlns="http://www.w3.org/2000/svg"></svg>',
         '<div class="hairline-tip"></div><script type="application/json" class="hairline-targets">', data,
         "</script><script>", interactive_asset("hairline.js"), "</script></figure>")
}

html_page <- function(title, fragment, surface = "#ffffff") {
  safe <- gsub("<", "&lt;", gsub("&", "&amp;", title %||% "", fixed = TRUE), fixed = TRUE)
  paste0('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1"><title>', safe,
         "</title><style>body{margin:0;padding:16px;background:", surface, "}</style></head><body>", fragment,
         "</body></html>\n")
}

write_html <- function(plot, path, size, size_mm, background) {
  if (!requireNamespace("svglite", quietly = TRUE)) {
    stop("hairline: HTML export needs the 'svglite' package", call. = FALSE)
  }
  svg_path <- tempfile(fileext = ".svg")
  on.exit(unlink(svg_path))
  draw_to_device(format_device("svg", svg_path, size_mm, 72, background), plot)
  svg <- paste(readLines(svg_path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  targets <- interactive_targets(plot, size, size_mm[1], size_mm[2])
  title <- plot@labels$title %||% ""
  alt <- figure_alt(plot)
  writeLines(html_page(title, figure_html(svg, targets, targets$style$font, alt), targets$style$surface), path,
             useBytes = TRUE)
}
