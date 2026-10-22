test_that("a family that is already a system font is used as it is, not registered again", {
  installed <- systemfonts::system_fonts()$family
  skip_if(length(installed) == 0, "no system fonts here")
  expect_false(register_font_family(installed[1], plain = font_file("400")))
})

test_that("a family that is no system font is registered", {
  family <- "Hairline Test Family"
  expect_true(register_font_family(family, plain = font_file("400")))
  expect_true(family %in% systemfonts::registry_fonts()$family)
})

test_that("the fontconfig file adds the bundled font folder to the default configuration", {
  lines <- readLines(fontconfig_file(NA, withr::local_tempfile(fileext = ".conf")))
  expect_true(any(grepl(system.file("fonts", package = "hairline"), lines, fixed = TRUE)))
  expect_true(any(grepl("/etc/fonts/fonts.conf", lines, fixed = TRUE)))
})

test_that("the fontconfig file builds on a configuration that was already chosen", {
  lines <- readLines(fontconfig_file("/opt/site/fonts.conf", withr::local_tempfile(fileext = ".conf")))
  expect_true(any(grepl("<include ignore_missing=\"yes\">/opt/site/fonts.conf</include>", lines, fixed = TRUE)))
  expect_false(any(grepl("/etc/fonts/fonts.conf", lines, fixed = TRUE)))
})

test_that("loading the package points fontconfig at the bundled font outside Windows", {
  skip_on_os("windows")
  expect_true(any(grepl(system.file("fonts", package = "hairline"), readLines(Sys.getenv("FONTCONFIG_FILE")),
                        fixed = TRUE)))
})

test_that("requested weights resolve to the face a family has, as the shared fixture says", {
  for (case in read_fixture("weights.json")) {
    expect_equal(nearest_weight(case$requested, unlist(case$available)), case$result, info = paste(case$requested, "of", paste(unlist(case$available), collapse = ", ")))
  }
})

test_that("the bundled family keeps its semibold; a family without one draws its bold", {
  family <- hl_tokens()$font$family
  expect_equal(family_weights(family), c(400, 500, 600))
  expect_equal(face_weight(family, 600), 600)
  skip_if_not("Helvetica Neue" %in% systemfonts::system_fonts()$family, "needs Helvetica Neue, which has no semibold")
  expect_equal(face_weight("Helvetica Neue", 600), 700)
  expect_equal(face_weight("Helvetica Neue", 500), 500)
})
