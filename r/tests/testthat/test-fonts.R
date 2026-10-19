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
