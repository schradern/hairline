# Interactive HTML, mirroring the Python interactive module: the static SVG plus targets for
# tooltips and series highlighting, drawn by the script shared with the Python package. Targets in pt from the top-left.

# Data layers that stay out of interactive targets (fit lines, density outlines, jittered points).
static_layer <- function(layer) {
  layer$hairline_static <- TRUE
  layer
}

interactive_numbers <- function(values, percent, digits = NULL) {
  if (percent) {
    digits <- digits %||% auto_digits(values * 100)
    return(vapply(values, function(value) hl_format_percent(round(value, 10), digits), character(1)))
  }
  digits <- digits %||% auto_digits(values)
  vapply(values, function(value) hl_format_number(round(value, 10), digits), character(1))
}

is_percent_scale <- function(scale) isTRUE(scale$hairline$percent)

# Values as their scale labels them: percentages on a share scale, with the scale's digits or the shared rule.
scale_numbers <- function(scale, values) interactive_numbers(values, is_percent_scale(scale), scale$hairline$digits)

# ISO dates in the data's own time zone, with the clock time when any point has one (and its seconds when any has
# those), so hourly or second-apart points stay apart.
datetime_texts <- function(values, zone) {
  moments <- as.POSIXct(round(values), origin = "1970-01-01", tz = zone %||% "UTC")
  seconds <- any(format(moments, "%S") != "00")
  timed <- seconds || any(format(moments, "%H:%M") != "00:00")
  format(moments, if (seconds) "%Y-%m-%d %H:%M:%S" else if (timed) "%Y-%m-%d %H:%M" else "%Y-%m-%d")
}

# X (or y) values as text: ISO dates on a date scale, category names on a discrete scale, else numbers.
axis_texts <- function(params, scale, values) {
  if (scale$is_discrete()) {
    labels <- params$get_labels()
    return(vapply(round(values), function(position) {
      if (position >= 1 && position <= length(labels)) as.character(labels[[position]]) else ""
    }, character(1)))
  }
  if (inherits(scale, "ScaleContinuousDate")) return(format(as.Date(values, origin = "1970-01-01"), "%Y-%m-%d"))
  if (inherits(scale, "ScaleContinuousDatetime")) return(datetime_texts(values, scale$timezone))
  scale_numbers(scale, values)
}

colour_hex <- function(colour) tolower(substr(grDevices::rgb(t(grDevices::col2rgb(colour)), maxColorValue = 255), 1, 7))

# "Series: x, y", or the values alone for a plot without a series name or title.
tip_text <- function(name, values) if (nzchar(name)) paste0(name, ": ", values) else values

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

# Missing values get no tip; ggplot leaves them out of the drawn line too.
# The stretches of a line between missing values, where ggplot breaks it: row numbers per stretch.
finite_runs <- function(rows) {
  finite <- which(is.finite(rows$x) & is.finite(rows$y))
  unname(split(finite, cumsum(c(1, diff(finite) > 1))))
}

line_targets <- function(data, geom, parts, plan, scaled) {
  if (!any(is.finite(data$x) & is.finite(data$y))) return(list())
  groups <- split(data, list(data$PANEL, data$group), drop = TRUE)
  groups <- Filter(function(rows) any(is.finite(rows$x) & is.finite(rows$y)), groups)
  lapply(groups, function(rows) {
    context <- panel_context(parts, plan, rows$PANEL[1])
    runs <- finite_runs(rows)
    paths <- lapply(runs, function(run) {
      if (geom == "GeomStep") step_points(rows$x[run], rows$y[run]) else cbind(rows$x[run], rows$y[run])
    })
    rows <- rows[unlist(runs), , drop = FALSE]
    name <- series_named(rows$colour[1], parts, context$index)
    xs <- axis_texts(context$params$x, context$x_scale, rows$x)
    ys <- scale_numbers(context$y_scale, rows$y)
    at <- context$to_pt(rows$x, rows$y)
    width <- rows$linewidth[1] * ggplot2::.pt * 0.75 * if (scaled) line_scale(context$box[3]) else 1
    list(name = name, color = colour_hex(rows$colour[1]),
         marks = lapply(paths, function(path) list(line = context$to_pt(path[, 1], path[, 2]), width = width)),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = at[index, ], text = tip_text(name, paste0(xs[index], ", ", ys[index])))
         }))
  })
}

point_targets <- function(data, parts, plan) {
  data <- data[data$shape %in% c(16, 19) & is.finite(data$x) & is.finite(data$y), , drop = FALSE]
  if (!nrow(data)) return(list())
  lapply(split(data, list(data$PANEL, data$colour), drop = TRUE), function(rows) {
    context <- panel_context(parts, plan, rows$PANEL[1])
    name <- series_named(rows$colour[1], parts, context$index)
    at <- context$to_pt(rows$x, rows$y)
    xs <- axis_texts(context$params$x, context$x_scale, rows$x)
    ys <- scale_numbers(context$y_scale, rows$y)
    radius <- rows$size[1] * ggplot2::.pt * 0.75 / 2
    list(name = name, color = colour_hex(rows$colour[1]),
         marks = lapply(seq_len(nrow(rows)), function(index) list(dot = at[index, ], r = radius)),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = at[index, ], text = tip_text(name, paste0(xs[index], ", ", ys[index])))
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
    # A bar's value with its sign: a bar (or stacked segment) that lies below zero is negative.
    values <- if (horizontal) ifelse(rows$xmax <= 0, rows$xmin - rows$xmax, rows$xmax - rows$xmin) else
      ifelse(rows$ymax <= 0, rows$ymin - rows$ymax, rows$ymax - rows$ymin)
    texts <- scale_numbers(if (horizontal) context$x_scale else context$y_scale, values)
    categories <- if (horizontal) axis_texts(context$params$y, context$y_scale, (rows$ymin + rows$ymax) / 2) else
      axis_texts(context$params$x, context$x_scale, (rows$xmin + rows$xmax) / 2)
    lefts <- pmin(top_left[, 1], bottom_right[, 1])
    tops <- pmin(top_left[, 2], bottom_right[, 2])
    widths <- abs(bottom_right[, 1] - top_left[, 1])
    heights <- abs(bottom_right[, 2] - top_left[, 2])
    list(name = name, color = colour_hex(rows$fill[1]),
         marks = lapply(seq_len(nrow(rows)), function(index) {
           list(rect = c(lefts[index], tops[index], widths[index], heights[index]))
         }),
         tips = lapply(seq_len(nrow(rows)), function(index) {
           list(at = c(lefts[index] + widths[index] / 2, tops[index]),
                text = tip_text(name, paste0(categories[index], ", ", texts[index])))
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
  with_plot_settings(plot, {
    framed <- frame_plan(plot, size, width_mm, height_mm, "html export")
    plot_targets(framed$parts, framed$plan)
  })
}

# Evaluates `code` with the settings the plot was made with (its locale for tooltip numbers), so a later change of
# the session's settings does not reach a plot made before it.
with_plot_settings <- function(plot, code) {
  settings <- plot@meta$hairline_settings
  if (is.null(settings)) return(code)
  previous <- hairline_state$settings
  hairline_state$settings <- settings
  on.exit(hairline_state$settings <- previous)
  code
}

interactive_asset <- function(name) {
  paste(readLines(system.file("interactive", name, package = "hairline"), encoding = "UTF-8", warn = FALSE),
        collapse = "\n")
}

face_weights <- c(400, 500, 600)

bundled_font_files <- function() {
  weights <- c(Regular = 400, Medium = 500, SemiBold = 600)
  files <- hl_tokens()$interactive$fonts
  data.frame(path = vapply(files, function(file) system.file("fonts", file, package = "hairline"), character(1)),
             low = unname(weights[sub("\\..*$", "", sub("^[^-]*-", "", files))]),
             high = unname(weights[sub("\\..*$", "", sub("^[^-]*-", "", files))]))
}

# The files the system draws `family` with, per weight (one file may serve several); a collection (.ttc) cannot be
# embedded and is left to the reader's installed fonts, as is a family that is not installed.
installed_font_files <- function(family) {
  if (!font_available(family)) return(data.frame(path = character(), low = numeric(), high = numeric()))
  paths <- systemfonts::match_fonts(family, weight = face_weights)$path
  usable <- grepl("\\.(ttf|otf)$", paths, ignore.case = TRUE, useBytes = TRUE)
  found <- unique(paths[usable])
  data.frame(path = found, low = vapply(found, function(path) min(face_weights[paths == path]), numeric(1)),
             high = vapply(found, function(path) max(face_weights[paths == path]), numeric(1)))
}

# The figure's font as data URIs under its own name, so the page renders with the font the layout was measured
# with: the bundled files for the bundled family, else the installed files of the requested one.
font_faces <- function(family) {
  files <- if (identical(family, hl_tokens()$font$family)) bundled_font_files() else installed_font_files(family)
  paste0(vapply(seq_len(nrow(files)), function(index) {
    path <- files$path[index]
    opentype <- grepl("\\.otf$", path, ignore.case = TRUE, useBytes = TRUE)
    weight <- if (files$low[index] == files$high[index]) files$low[index] else
      paste(files$low[index], files$high[index])
    data <- jsonlite::base64_enc(readBin(path, "raw", file.info(path)$size))
    sprintf("@font-face{font-family:'%s';font-weight:%s;src:url(data:%s;base64,%s) format('%s')}", family, weight,
            if (opentype) "font/otf" else "font/ttf", gsub("\n", "", data), if (opentype) "opentype" else "truetype")
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
