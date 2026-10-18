example_brand <- function() testthat::test_path("fixtures", "example_brand.yml")

write_brand <- function(folder, adapt = "readable", categorical = c("harbor", "poppy", "glacier", "fern"),
                        glacier = "#8cc8ff") {
  lines <- c("meta:", "  name: Example University Hospital", "color:", "  palette:", "    harbor: \"#0b3d6e\"",
             "    poppy: \"#f2545b\"", sprintf("    glacier: \"%s\"", glacier), "    fern: \"#7fd8a0\"",
             "  foreground: harbor", "defaults:", "  hairline:",
             sprintf("    categorical: [%s]", paste(categorical, collapse = ", ")), sprintf("    adapt: %s", adapt))
  path <- file.path(folder, "_brand.yml")
  writeLines(lines, path)
  path
}

test_that("example brand matches the Python reference exactly", {
  expected <- read_fixture("brand.json")
  brand <- hl_load_brand(example_brand())
  expect_equal(brand$name, expected$name)
  expect_equal(brand$names, as_colors(expected$names))
  expect_equal(brand$colors_given, as_colors(expected$colors_given))
  expect_equal(brand$colors_used, as_colors(expected$readable))
  expect_equal(brand$neutral$ink, expected$neutral$ink)
  expect_equal(brand$locale, expected$locale)
  expect_true(hl_check_palette(brand$colors_used)$passed)
})

test_that("exact mode warns about light slots and keeps colours", {
  expect_warning(brand <- hl_load_brand(write_brand(withr::local_tempdir(), adapt = "exact")), "glacier.*below 3:1")
  expect_equal(brand$colors_used, brand$colors_given)
})

test_that("malformed brand files name the file, key and value", {
  folder <- withr::local_tempdir()
  expect_error(hl_load_brand(write_brand(folder, glacier = "#8cc8f")),
               "_brand.yml: color.palette.glacier: '#8cc8f' is not a 6-digit hex colour", fixed = TRUE)
  expect_error(hl_load_brand(write_brand(folder, categorical = c("harbor", "poppy", "ice"))),
               "defaults.hairline.categorical[2]: 'ice' is not in color.palette", fixed = TRUE)
  expect_error(hl_load_brand(write_brand(folder, adapt = "strict")), "'strict' must be 'exact' or 'readable'")
  path <- file.path(folder, "broken", "_brand.yml")
  dir.create(dirname(path))
  writeLines(c("color:", "  palette: [unclosed"), path)
  expect_error(hl_load_brand(path), "_brand.yml: line")
})

test_that("lookup stops at the project root and hl_use applies the brand", {
  root <- withr::local_tempdir()
  project <- file.path(root, "project")
  dir.create(file.path(project, "analysis", "deep"), recursive = TRUE)
  file.create(file.path(project, "DESCRIPTION"))
  file.copy(example_brand(), file.path(root, "_brand.yml"))
  expect_null(hl_find_brand(file.path(project, "analysis", "deep")))
  file.copy(example_brand(), file.path(project, "_brand.yml"))
  expect_equal(normalizePath(hl_find_brand(file.path(project, "analysis", "deep"))),
               normalizePath(file.path(project, "_brand.yml")))
  withr::local_dir(file.path(project, "analysis"))
  expect_message(settings <- hl_use(), "Using brand 'Example University Hospital'")
  expect_equal(settings$locale, "de")
  expect_equal(hl_use(locale = "en", palette = "lagoon")$palette_name, "lagoon")
  expect_null(hl_use(brand = FALSE)$brand_name)
})

test_that("brand slot guard and report", {
  hl_use(brand = example_brand())
  expect_error(hl_palette(n = 5), "brand 'Example University Hospital' has 4 slots but 5 categories", fixed = TRUE)
  report <- hl_brand_report()
  expect_match(report, "harbor")
  expect_match(report, "checks: passed")
  hl_use(brand = FALSE)
})

test_that("brand layers, export overrides and entity checks match the Python reference", {
  expected <- read_fixture("brand.json")$layered
  paths <- c(example_brand(), testthat::test_path("fixtures", "example_units.yml"))
  brand <- hl_load_brand(paths)
  expect_equal(brand$name, expected$name)
  expect_equal(as.list(brand$entity_colors), expected$entity_colors)
  expect_equal(brand$entity_failures, as.character(unlist(expected$entity_failures)))
  expect_equal(hl_load_brand(paths, output = "docx")$base_size, expected$docx_base_size)
  expect_equal(hl_load_brand(paths, output = "html")$neutral$grid, expected$html_grid)
  expect_warning(exact <- checked_entities(c("Unit A" = "#0b3d6e", "Unit B" = "#1d4f86"), "exact", "test"),
                 "hard to tell apart")
  expect_equal(exact$failures, as.character(unlist(expected$exact_failures)))
  expect_error(hl_load_brand(paths, output = "slides"), "output 'slides' must be one of screen, pdf, html, docx")
})

test_that("the report names the layer each value came from, as in Python", {
  expected <- read_fixture("brand.json")$layered$report
  paths <- c(example_brand(), testthat::test_path("fixtures", "example_units.yml"))
  lines <- strsplit(hl_brand_report(hl_load_brand(paths)), "\n", fixed = TRUE)[[1]]
  expect_equal(lines[2:3], paste0("layer ", 1:2, ": ", normalizePath(paths)))
  expect_equal(sub("^(layer [0-9]+): .*$", "\\1", lines), unlist(expected))
})

test_that("an export override is named with its layer", {
  folder <- withr::local_tempdir()
  writeLines(c("color:", "  palette:", "    harbor: \"#0b3d6e\"", "    poppy: \"#f2545b\"", "defaults:", "  hairline:",
               "    categorical: [harbor, poppy]"), file.path(folder, "_brand.yml"))
  writeLines(c("defaults:", "  hairline:", "    outputs:", "      docx:", "        colors:", "          Unit A: poppy"),
             file.path(folder, "project.yml"))
  report <- hl_brand_report(hl_load_brand(file.path(folder, c("_brand.yml", "project.yml")), output = "docx"))
  entity <- grep("^entity Unit A:", strsplit(report, "\n", fixed = TRUE)[[1]], value = TRUE)
  expect_true(endsWith(entity, "(layer 2, docx)"))
})
