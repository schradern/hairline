process_steps <- function(...) {
  rows <- data.frame(lane = c("Ward", "Laboratory", "Ward", "Physician"),
                     step = c("Draw sample", "Analyse", "See result", "Read result"),
                     status = c("", "", "highlight", "tentative"),
                     note = c("", "Runs around the clock.", "", "Not yet on the phone."))
  extra <- list(...)
  for (name in names(extra)) rows[[name]] <- extra[[name]]
  rows
}

process_flows <- function(...) {
  rows <- data.frame(source = c("Draw sample", "Analyse", "See result"),
                     target = c("Analyse", "See result", "Read result"), how = c("Courier", "", "Phone"),
                     status = c("", "highlight", "tentative"))
  extra <- list(...)
  for (name in names(extra)) rows[[name]] <- extra[[name]]
  rows
}

process_shapes <- function(plot) {
  plot@meta$hairline_drawing(c(10, 10, 460, 300), measure_for(hl_settings()), drawing_style(hl_settings()))
}

process_texts <- function(shapes, part) {
  vapply(Filter(function(shape) identical(shape$part, part), shapes), `[[`, "", "text")
}

process_role <- function(shapes, role) Filter(function(shape) identical(shape$role, role), shapes)

test_that("routes match the shared fixture", {
  fixture <- read_fixture("process.json")
  cells <- vapply(fixture$cells, function(cell) paste(cell[[1]], cell[[2]]), "")
  turns <- as.numeric(unlist(fixture$turns))
  for (route in fixture$routes) {
    corners <- process_path(fixture$places[[route$source + 1]], fixture$places[[route$target + 1]], cells, turns, "")
    arrow <- process_head(process_rounded(corners, fixture$radius, fixture$steps), fixture$head)
    expect_equal(as.numeric(t(arrow$line)), as.numeric(unlist(route$line)), tolerance = 1e-9)
    expect_equal(as.numeric(t(arrow$tip)), as.numeric(unlist(route$tip)), tolerance = 1e-9)
  }
})

test_that("stages follow the longest path in the shared fixture", {
  fixture <- read_fixture("process.json")
  expect_equal(process_derived_stages(length(fixture$places), fixture$flows, ""), as.numeric(unlist(fixture$stages)))
})

test_that("steps stand in their lanes and stages", {
  shapes <- process_shapes(hl_process(process_steps(), process_flows(), status = "status", note = "note",
                                      label = "how"))
  expect_equal(process_texts(shapes, "lane"), c("Ward", "Laboratory", "Physician"))
  boxes <- process_role(shapes, "step")
  names(boxes) <- vapply(boxes, `[[`, "", "series")
  lefts <- vapply(boxes[c("Draw sample", "Analyse", "See result", "Read result")], function(box) box$points[1, 1], 0)
  expect_equal(unname(lefts), sort(unname(lefts)))
  expect_length(unique(lefts), 4)
  expect_equal(boxes[["Draw sample"]]$points[1, 2], boxes[["See result"]]$points[1, 2])
})

test_that("status marks steps and flows", {
  shapes <- process_shapes(hl_process(process_steps(), process_flows(), status = "status", note = "note",
                                      label = "how"))
  boxes <- process_role(shapes, "step")
  names(boxes) <- vapply(boxes, `[[`, "", "series")
  expect_gt(boxes[["See result"]]$edge_width, boxes[["Draw sample"]]$edge_width)
  expect_null(boxes[["Read result"]]$edge)
  expect_equal(lapply(process_role(shapes, "step_edge"), `[[`, "dash"), list(c(2, 2)))
  lines <- process_role(shapes, "flow")
  expect_gt(lines[[2]]$width, lines[[1]]$width)
  expect_false(identical(lines[[2]]$color, lines[[1]]$color))
  expect_false(is.null(lines[[3]]$dash))
})

test_that("notes are numbered in reading order and listed", {
  shapes <- process_shapes(hl_process(process_steps(), process_flows(), status = "status", note = "note",
                                      label = "how"))
  expect_equal(process_texts(shapes, "marker"), c("1", "2", "1", "2"))
  expect_equal(process_texts(shapes, "note"), c("Runs around the clock.", "Not yet on the phone."))
  expect_equal(process_texts(shapes, "flow_label"), c("Courier", "Phone"))
})

test_that("a flow within a stage runs up or down", {
  steps <- data.frame(lane = c("Laboratory", "Ward"), step = c("Phone", "Take call"), stage = c(1, 1))
  shapes <- process_shapes(hl_process(steps, data.frame(source = "Phone", target = "Take call"), stage = "stage",
                                      lanes = c("Ward", "Laboratory")))
  line <- process_role(shapes, "flow")[[1]]$points
  expect_equal(line[1, 1], line[nrow(line), 1])
  expect_lt(line[nrow(line), 2], line[1, 2])
})

test_that("sections stack versions on the same lanes", {
  steps <- rbind(process_steps(version = "Before"), process_steps(version = "After"))
  flows <- rbind(process_flows(version = "Before"), process_flows(version = "After")[c(1, 3, 2), ])
  plot <- hl_process(steps, flows, section = "version", note = "note")
  shapes <- process_shapes(plot)
  expect_equal(process_texts(shapes, "section"), c("Before", "After"))
  expect_equal(process_texts(shapes, "marker"), c("1", "2", "1", "2", "3", "4", "3", "4"))
  expect_equal(plot@meta$hairline_description, paste("Process diagram. Lanes: Ward, Laboratory, Physician.",
                                                     "Before: 4 steps, 3 flows. After: 4 steps, 3 flows."))
})

test_that("steps carry their lane and note as their tooltip", {
  shapes <- process_shapes(hl_process(process_steps(), process_flows(), note = "note"))
  boxes <- process_role(shapes, "step")
  names(boxes) <- vapply(boxes, `[[`, "", "series")
  expect_equal(boxes[["Analyse"]]$tip, "Analyse\nLaboratory\nRuns around the clock.")
})

test_that("the description is German in a German figure", {
  on.exit(hl_use(brand = FALSE))
  hl_use(brand = FALSE, locale = "de")
  plot <- hl_process(process_steps(), process_flows(), status = "status")
  expect_equal(plot@meta$hairline_description,
               paste("Prozessdiagramm. Bahnen: Ward, Laboratory, Physician. 4 Schritte, 3 Übergänge.",
                     "Hervorgehoben: See result."))
})

test_that("process refuses what it cannot draw", {
  expect_error(hl_process(process_steps(status = c("", "", "new", "")), status = "status"), "status 'new'")
  expect_error(hl_process(process_steps(step = c("A", "A", "B", "C"))), "appears twice")
  expect_error(hl_process(process_steps(), process_flows(target = c("Analyse", "Nowhere", "Read result"))),
               "'Nowhere', which is not a step")
  expect_error(hl_process(process_steps(), process_flows(target = c("Analyse", "Analyse", "Read result"))),
               "returns to itself")
  expect_error(hl_process(process_steps(), data.frame(source = c("Analyse", "Draw sample"),
                                                      target = c("Draw sample", "Analyse"))), "in a loop")
  expect_error(hl_process(process_steps(stage = c(1, 2, 1, 3)), stage = "stage"),
               "share lane 'Ward' and stage 1")
  expect_error(hl_process(process_steps(stage = 1:4), data.frame(source = "Analyse", target = "Draw sample"),
                          stage = "stage"), "runs back from stage 2 to 1")
  expect_error(hl_process(process_steps(stage = c("a", "b", "c", "d")), stage = "stage"), "needs a number")
  crossing <- data.frame(lane = "Ward", step = c("A", "B", "C"), stage = 1:3)
  expect_error(hl_process(crossing, data.frame(source = "A", target = "C"), stage = "stage"),
               "from 'A' to 'C' would cross another step")
})

test_that("too many stages for the width is a layout error", {
  steps <- data.frame(lane = "Ward", step = paste("Step", 0:11))
  flows <- data.frame(source = steps$step[-12], target = steps$step[-1])
  expect_error(hl_process(steps, flows)@meta$hairline_drawing(c(0, 0, 220, 300), measure_for(hl_settings()),
                                                              drawing_style(hl_settings())), "12 stages need")
})
