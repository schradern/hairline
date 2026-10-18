sample_hairline_plot <- function() {
  ggplot2::ggplot(mtcars, ggplot2::aes(wt, mpg)) + ggplot2::geom_point() +
    ggplot2::labs(title = "Survival after ICU discharge", caption = "Synthetic data") + theme_hairline()
}

test_that("default outputs are PDF and 600 dpi PNG in a created folder", {
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  paths <- suppressWarnings(hl_save(sample_hairline_plot(), file.path(folder, "nested", "survival")))
  expect_equal(tools::file_ext(paths), c("pdf", "png"))
  expect_true(all(file.exists(paths)))
  expect_equal(attr(png::readPNG(paths[2], info = TRUE), "info")$dpi, c(600, 600), tolerance = 0.5)
})

test_that("PDF output has no timestamp or producer banner", {
  hl_use(brand = FALSE)
  path <- suppressWarnings(hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "a"), formats = "pdf"))
  bytes <- readBin(path, "raw", file.size(path))
  expect_false(grepl("CreationDate|Producer", rawToChar(bytes[bytes != as.raw(0)]), useBytes = TRUE))
})

test_that("PDF output is byte-stable on the cairo route", {
  skip_if_not(pdf_route() == "cairo", "the svglite + rsvg fallback route is not byte-stable")
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  first <- without_pdf_font_warning(hl_save(sample_hairline_plot(), file.path(folder, "a"), formats = "pdf"))
  second <- without_pdf_font_warning(hl_save(sample_hairline_plot(), file.path(folder, "b"), formats = "pdf"))
  first_bytes <- readBin(first, "raw", file.size(first))
  skip_if(pdf_has_object_streams(first_bytes), "this cairo keeps its creation date in a compressed object stream")
  expect_identical(first_bytes, readBin(second, "raw", file.size(second)))
})

# The bundled font reaches a PDF through fontconfig (cairo outside Windows) or once it is installed for the user.
pdf_sees_bundled_font <- function() {
  (pdf_route() == "cairo" && .Platform$OS.type != "windows") || font_installed_for_pdf()
}

test_that("PDF embeds the bundled font where the PDF route can see it", {
  hl_use(brand = FALSE)
  skip_if_not(pdf_sees_bundled_font(), "no PDF route that sees the bundled font here")
  path <- hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "pdf")
  expect_true(pdf_contains(readBin(path, "raw", file.size(path)), "HairlineSans"))
})

test_that("a PDF without the bundled font warns and points to hl_install_font()", {
  hl_use(brand = FALSE)
  skip_if(pdf_sees_bundled_font(), "the bundled font reaches the PDF here")
  expect_warning(hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "pdf"),
                 "hl_install_font")
})

test_that("SVG keeps text as text and is byte-stable", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  folder <- withr::local_tempdir()
  first <- hl_save(sample_hairline_plot(), file.path(folder, "a"), formats = "svg")
  second <- hl_save(sample_hairline_plot(), file.path(folder, "b"), formats = "svg")
  expect_true(any(grepl("Survival after ICU discharge", readLines(first, warn = FALSE), fixed = TRUE)))
  expect_identical(readLines(first, warn = FALSE), readLines(second, warn = FALSE))
})

test_that("unknown formats are refused before anything is written", {
  folder <- withr::local_tempdir()
  expect_error(hl_save(sample_hairline_plot(), file.path(folder, "out", "f"), formats = c("png", "jpeg")),
               "unknown format 'jpeg'; use one of pdf, png, svg, tiff", fixed = TRUE)
  expect_false(dir.exists(file.path(folder, "out")))
})

test_that("TIFF is LZW-compressed and the size preset sets the base size", {
  hl_use(brand = FALSE)
  path <- hl_save(sample_hairline_plot(), file.path(withr::local_tempdir(), "f"), formats = "tiff", dpi = 72)
  expect_true(file.exists(path))
  expect_equal(saved_settings(sample_hairline_plot(), "single")$base_size, 8)
  hl_use(base_size = 10, brand = FALSE)
  expect_equal(saved_settings(sample_hairline_plot(), "single")$base_size, 10)
})

test_that("hl_install_font copies the bundled files into the user font folder", {
  home <- withr::local_tempdir()
  withr::local_envvar(HOME = home, LOCALAPPDATA = home)
  paths <- hl_install_font(confirm = FALSE)
  expect_length(paths, 6)
  expect_true(all(file.exists(paths)))
  expect_true(all(startsWith(paths, normalizePath(home))))
})

named_plot <- function(subtitle = "Kaplan–Meier estimate") sample_hairline_plot() + ggplot2::labs(subtitle = subtitle)
named_title <- "Survival after ICU discharge"
named_description <- "Survival after ICU discharge. Kaplan–Meier estimate"

test_that("PNG and SVG files are named by title and subtitle", {
  skip_if_not_installed("svglite")
  skip_if_not_installed("png")
  hl_use(brand = FALSE)
  paths <- hl_save(named_plot(), file.path(withr::local_tempdir(), "named"), formats = c("png", "svg"))
  text <- attr(png::readPNG(paths[1], info = TRUE), "info")$text
  Encoding(text) <- "UTF-8"
  expect_equal(unname(text[c("Title", "Description")]), c(named_title, named_description))
  svg <- paste(readLines(paths[2], encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(grepl(paste0("<title>", named_title, "</title><desc>", named_description, "</desc>"), svg, fixed = TRUE))
})

test_that("the SVG name is escaped", {
  skip_if_not_installed("svglite")
  hl_use(brand = FALSE)
  path <- hl_save(named_plot("Dose < 5 & > 1"), file.path(withr::local_tempdir(), "escaped"), formats = "svg")
  svg <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  expect_true(grepl("<desc>Survival after ICU discharge. Dose &lt; 5 &amp; &gt; 1</desc>", svg, fixed = TRUE))
})

test_that("the PDF's last info dictionary holds the title and subject and nothing else", {
  hl_use(brand = FALSE)
  path <- suppressWarnings(hl_save(named_plot(), file.path(withr::local_tempdir(), "info"), formats = "pdf"))
  bytes <- readBin(path, "raw", file.size(path))
  section <- pdf_last_section(bytes)
  info <- grepRaw("/Info [0-9]+ 0 R", bytes, value = TRUE, all = TRUE)
  number <- sub("/Info ([0-9]+) 0 R", "\\1", rawToChar(info[[length(info)]]))
  start <- grepRaw(paste0("\n", number, " 0 obj\n<< "), bytes, all = TRUE)
  dictionary <- rawToChar(bytes[start[length(start)]:grepRaw(">>", bytes, offset = start[length(start)])])
  expect_true(grepl(paste0("/Title ", pdf_text(named_title)), dictionary, fixed = TRUE))
  expect_true(grepl(paste0("/Subject ", pdf_text(named_description)), dictionary, fixed = TRUE))
  expect_false(grepl("Producer|CreationDate", dictionary))
  expect_gt(section$offset, 0)
})

test_that("PDF readers see the title and subject, and no producer or timestamp", {
  skip_on_cran()
  skip_if(Sys.which("pdfinfo") == "", "poppler's pdfinfo is not installed")
  hl_use(brand = FALSE)
  path <- suppressWarnings(hl_save(named_plot(), file.path(withr::local_tempdir(), "read"), formats = "pdf"))
  info <- system2("pdfinfo", shQuote(path), stdout = TRUE)
  Encoding(info) <- "UTF-8"
  expect_true(paste0("Title:           ", named_title) %in% info)
  expect_true(paste0("Subject:         ", named_description) %in% info)
  expect_false(any(grepl("^(Producer|CreationDate):", info)))
})

test_that("the description leaves out an empty subtitle, as in Python", {
  plot <- sample_hairline_plot() + ggplot2::labs(subtitle = "")
  expect_equal(figure_name(plot), c(named_title, named_title))
  expect_null(figure_name(sample_hairline_plot() + ggplot2::labs(title = NA_character_)))
})

test_that("a subtitle alone is the alt text, as in Python", {
  plot <- sample_hairline_plot() + ggplot2::labs(title = NULL, subtitle = "Weekly counts")
  expect_equal(figure_alt(plot), "Weekly counts")
  expect_null(figure_name(plot))
})

test_that("a font name inside a compressed object stream is found", {
  hidden <- c(charToRaw("1 0 obj\n<< /Type /ObjStm /Filter /FlateDecode >>\nstream\n"),
              memCompress(charToRaw("<< /BaseFont /ABCDEF+HairlineSans >>"), "gzip"),
              charToRaw("\nendstream\nendobj\n"))
  expect_length(grepRaw("HairlineSans", hidden, fixed = TRUE), 0)
  expect_true(pdf_contains(hidden, "HairlineSans"))
  expect_false(pdf_contains(hidden, "PublicSans"))
})

test_that("PNG text is Latin-1 only when every character is, as the PNG format defines it", {
  chunk_type <- function(text) rawToChar(png_text_chunk("Description", text)[5:8])
  expect_equal(chunk_type("Caf\u00e9 au lait"), "tEXt")
  expect_equal(chunk_type("Kaplan\u2013Meier estimate"), "iTXt")
  expect_true(as.raw(0xe9) %in% png_text_chunk("Title", "Caf\u00e9"))
})
