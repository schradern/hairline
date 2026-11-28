# Process diagram: who does which step (one lane per role), in which order (stages left to right), and how each step
# hands on to the next. Mirrors the Python package's charts/process.py; lanes and stages count from 0 in the spec,
# as there.

process_statuses <- c("highlight", "tentative")

# A step's or flow's status: "highlight", "tentative", or NULL for a plain one (an empty cell). As Python's
# status_of().
process_status <- function(value, what) {
  if (is.null(value) || is.na(value) || identical(as.character(value), "")) return(NULL)
  if (!as.character(value) %in% process_statuses) {
    stop(sprintf("hairline: process: %s has status '%s'; use 'highlight', 'tentative' or leave it empty", what,
                 as.character(value)), call. = FALSE)
  }
  as.character(value)
}

process_text <- function(value) if (is.null(value) || is.na(value)) "" else as.character(value)

process_section_steps <- function(rows, columns, lanes, where) {
  names <- as.character(rows[[columns$step]])
  repeated <- unique(names[duplicated(names)])
  if (length(repeated)) {
    stop(sprintf("hairline: process: step '%s' appears twice%s; name each step once", repeated[1], where),
         call. = FALSE)
  }
  lapply(seq_along(names), function(index) {
    list(name = names[index], lane = match(as.character(rows[[columns$lane]][index]), lanes) - 1,
         status = if (!is.null(columns$status)) process_status(rows[[columns$status]][index],
                                                                sprintf("step '%s'", names[index])),
         note_text = if (!is.null(columns$note)) process_text(rows[[columns$note]][index]) else "",
         stage = if (!is.null(columns$stage)) rows[[columns$stage]][index])
  })
}

process_section_flows <- function(rows, steps, columns, where) {
  if (is.null(rows)) return(list())
  names <- vapply(steps, `[[`, "", "name")
  flows <- list()
  seen <- character()
  for (index in seq_len(nrow(rows))) {
    ends <- c(as.character(rows[[columns$source]][index]), as.character(rows[[columns$target]][index]))
    unknown <- setdiff(ends, names)
    if (length(unknown)) {
      stop(sprintf("hairline: process: a flow names '%s', which is not a step%s; steps: %s", unknown[1], where,
                   paste(names, collapse = ", ")), call. = FALSE)
    }
    if (ends[1] == ends[2]) {
      stop(sprintf("hairline: process: the flow from '%s' returns to itself%s", ends[1], where), call. = FALSE)
    }
    key <- paste(ends, collapse = "\r")
    if (key %in% seen) {
      stop(sprintf("hairline: process: the flow from '%s' to '%s' appears twice%s", ends[1], ends[2], where),
           call. = FALSE)
    }
    seen <- c(seen, key)
    flows[[length(flows) + 1]] <- list(
      source = match(ends[1], names) - 1, target = match(ends[2], names) - 1,
      label = if (!is.null(columns$label)) process_text(rows[[columns$label]][index]) else "",
      status = if (!is.null(columns$flow_status)) process_status(rows[[columns$flow_status]][index],
                                                                 sprintf("the flow from '%s'", ends[1])))
  }
  flows
}

# Each step one stage after the latest step that hands on to it (the longest path), steps nothing hands on to at
# stage 0; a loop has no order and is an error. As Python's derived_stages().
process_derived_stages <- function(count, flows, where) {
  incoming <- lapply(seq_len(count) - 1, function(step) {
    vapply(Filter(function(flow) flow$target == step, flows), function(flow) flow$source, numeric(1))
  })
  stages <- rep(NA_real_, count)
  for (pass in seq_len(count)) {
    for (step in seq_len(count)) {
      sources <- incoming[[step]] + 1
      if (is.na(stages[step]) && !anyNA(stages[sources])) {
        stages[step] <- if (length(sources)) max(stages[sources] + 1) else 0
      }
    }
  }
  if (anyNA(stages)) {
    stop(sprintf("hairline: process: the flows run in a loop%s; give stage = to place the steps", where),
         call. = FALSE)
  }
  stages
}

# Stages from the data, as positions: the distinct values in order become stages 0, 1, 2, ... As Python's
# given_stages().
process_given_stages <- function(sections, column) {
  values <- unlist(lapply(sections, function(section) lapply(section$steps, `[[`, "stage")))
  if (!is.numeric(values) || length(values) != sum(vapply(sections, function(s) length(s$steps), 0)) ||
      anyNA(values)) {
    stop(sprintf("hairline: process: '%s' needs a number for every step (1, 2, 3, ... from left to right)", column),
         call. = FALSE)
  }
  places <- sort(unique(values))
  lapply(sections, function(section) {
    section$steps <- lapply(section$steps, function(step) {
      step$stage <- match(step$stage, places) - 1
      step
    })
    section
  })
}

# One step per lane and stage, and flows that run left to right or up and down within a stage without crossing
# another step. As Python's check_places().
process_check_places <- function(section, lanes, where) {
  cells <- character()
  owners <- character()
  for (step in section$steps) {
    cell <- paste(step$lane, step$stage)
    if (cell %in% cells) {
      stop(sprintf("hairline: process: '%s' and '%s' share lane '%s' and stage %d%s; give them different stages",
                   owners[match(cell, cells)], step$name, lanes[step$lane + 1], step$stage + 1, where), call. = FALSE)
    }
    cells <- c(cells, cell)
    owners <- c(owners, step$name)
  }
  for (flow in section$flows) {
    source <- section$steps[[flow$source + 1]]
    target <- section$steps[[flow$target + 1]]
    if (target$stage < source$stage) {
      stop(sprintf(paste0("hairline: process: the flow from '%s' to '%s' runs back from stage %d to %d%s; flows run ",
                          "left to right, or up and down within a stage"), source$name, target$name,
                   source$stage + 1, target$stage + 1, where), call. = FALSE)
    }
    process_route_kind(source, target, cells, where)
  }
}

# Notes numbered 1, 2, ... in reading order: by section, then stage, then lane. As Python's number_notes().
process_number_notes <- function(sections) {
  number <- 0
  lapply(sections, function(section) {
    noted <- which(vapply(section$steps, function(step) nzchar(step$note_text), logical(1)))
    stages <- vapply(section$steps[noted], `[[`, 0, "stage")
    lanes <- vapply(section$steps[noted], `[[`, 0, "lane")
    section$notes <- list()
    for (index in noted[order(stages, lanes)]) {
      number <<- number + 1
      section$steps[[index]]$note <- number
      step <- section$steps[[index]]
      section$notes[[length(section$notes) + 1]] <- list(number = number, text = step$note_text,
                                                         status = step$status)
    }
    section
  })
}

process_rows <- function(data, column, name) if (is.null(column)) data else data[as.character(data[[column]]) == name, ]

# Lanes, the number of stages and each section's steps (lane, stage, status, note number) and flows. As Python's
# process_spec().
process_spec <- function(steps, flows, columns, lanes) {
  check_columns(steps, columns[c("lane", "step", "stage", "section", "status", "note")])
  if (!is.null(flows)) check_columns(flows, columns[c("source", "target", "label", "section")])
  if (!is.null(flows) && !is.null(columns$status) && columns$status %in% names(flows)) {
    columns$flow_status <- columns$status
  }
  names <- ordered_names(as.character(steps[[columns$lane]]), lanes, "process", columns$lane, complete = TRUE)
  section_names <- if (is.null(columns$section)) list(NULL) else as.list(group_names(steps[[columns$section]]))
  sections <- lapply(section_names, function(name) {
    where <- if (is.null(name)) "" else sprintf(" in section '%s'", name)
    found <- process_section_steps(process_rows(steps, columns$section, name), columns, names, where)
    moved <- if (is.null(flows)) NULL else process_rows(flows, columns$section, name)
    list(name = name, steps = found, flows = process_section_flows(moved, found, columns, where), where = where)
  })
  if (!is.null(columns$stage)) sections <- process_given_stages(sections, columns$stage)
  sections <- lapply(sections, function(section) {
    if (is.null(columns$stage)) {
      stages <- process_derived_stages(length(section$steps), section$flows, section$where)
      for (index in seq_along(stages)) section$steps[[index]]$stage <- stages[index]
    }
    process_check_places(section, names, section$where)
    section$where <- NULL
    section
  })
  sections <- process_number_notes(sections)
  stages <- unlist(lapply(sections, function(section) vapply(section$steps, `[[`, 0, "stage")))
  list(lanes = names, stages = 1 + max(stages), sections = sections, accent = lone_colour())
}

#' Process diagram in swimlanes
#'
#' One lane per role, steps left to right in stages, flows handing on from step to step. Highlighted steps and
#' flows mark what changed, tentative ones what is absent or open; a note numbers a step and lists its text below
#' the lanes. Sections stack versions of one process (before, after) on the same lanes and stages.
#'
#' @param steps Data frame with one row per step.
#' @param flows Data frame with one row per flow, or NULL.
#' @param lane Column of `steps` naming who does the step.
#' @param step Column of `steps` with the step's name.
#' @param stage Column of `steps` whose numbers place the steps left to right; a flow within a stage runs up or down.
#'   Without it each step stands one stage after the latest step handing on to it.
#' @param section Column (in `steps` and `flows`) whose values stack versions of the process.
#' @param status Column (in `steps` and, where it has it, in `flows`): "highlight", "tentative" or empty.
#' @param note Column of `steps` with a note; the step gets its number and the note is listed below the lanes.
#' @param source,target Columns of `flows` naming the steps a flow runs from and to.
#' @param label Column of `flows` naming how a step hands on.
#' @param lanes Order of the lanes; the rest follow in data order.
#' @param title,subtitle,caption Frame texts.
#' @return A ggplot with the hairline frame.
#' @examples
#' steps <- data.frame(lane = c("Ward", "Laboratory", "Ward"), step = c("Draw sample", "Analyse", "Read result"),
#'                     status = c("", "", "highlight"))
#' flows <- data.frame(source = c("Draw sample", "Analyse"), target = c("Analyse", "Read result"))
#' hl_process(steps, flows, status = "status")
#' @export
hl_process <- function(steps, flows = NULL, lane = "lane", step = "step", stage = NULL, section = NULL, status = NULL,
                       note = NULL, source = "source", target = "target", label = NULL, lanes = NULL, title = NULL,
                       subtitle = NULL, caption = NULL) {
  columns <- list(lane = lane, step = step, stage = stage, section = section, status = status, note = note,
                  source = source, target = target, label = label)
  spec <- process_spec(steps, flows, columns, lanes)
  plot <- ggplot2::ggplot() + ggplot2::geom_blank() +
    ggplot2::labs(title = title %||% "Process", subtitle = subtitle, caption = caption, x = NULL, y = NULL) +
    theme_hairline(axes = FALSE)
  plot@meta$hairline_drawing <- function(box, measure, style) process_drawing(spec, box, measure, style)
  plot@meta$hairline_fit_height <- TRUE
  plot@meta$hairline_description <- process_description(spec)
  plot
}
