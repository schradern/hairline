# Each saved file names its figure, as the Python package's save() does: PDF Title and Subject, PNG Title and
# Description, SVG <title> and <desc>. The description is the title and subtitle, the alt text that the HTML figure
# and the host manifest give.

is_text <- function(value) is.character(value) && length(value) == 1 && !is.na(value) && nzchar(value)

# The figure's alt text: title and subtitle, leaving out a missing or empty one.
figure_alt <- function(plot) {
  labels <- if (ggplot2::is_ggplot(plot)) plot@labels else list()
  enc2utf8(paste(unlist(Filter(is_text, list(labels$title, labels$subtitle))), collapse = ". "))
}

figure_name <- function(plot) {
  title <- if (ggplot2::is_ggplot(plot)) plot@labels$title
  if (!is_text(title)) return(NULL)
  c(enc2utf8(title), figure_alt(plot))
}

# PDF files are named while they are written (write_pdf), the other formats after their device closes.
name_file <- function(path, format, naming) {
  if (is.null(naming)) return(invisible(path))
  if (format == "png") name_png(path, naming)
  if (format == "svg") name_svg(path, naming)
  invisible(path)
}

xml_text <- function(text) {
  gsub(">", "&gt;", gsub("<", "&lt;", gsub("&", "&amp;", text, fixed = TRUE), fixed = TRUE), fixed = TRUE)
}

name_svg <- function(path, naming) {
  text <- paste(readLines(path, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  end <- regexpr(">", substring(text, regexpr("<svg", text, fixed = TRUE)), fixed = TRUE) +
    regexpr("<svg", text, fixed = TRUE) - 1
  named <- paste0(substr(text, 1, end), "<title>", xml_text(naming[1]), "</title><desc>", xml_text(naming[2]),
                  "</desc>", substring(text, end + 1))
  writeLines(enc2utf8(named), path, useBytes = TRUE)
}

# CRC-32 of PNG chunks, on 16-bit halves so every step stays within R's 32-bit signed integers.
crc_table <- function() {
  if (is.null(hairline_state$crc_table)) {
    hairline_state$crc_table <- t(vapply(0:255, function(index) {
      high <- 0L
      low <- index
      for (step in 1:8) {
        odd <- bitwAnd(low, 1L) == 1L
        low <- bitwOr(bitwShiftR(low, 1L), bitwShiftL(bitwAnd(high, 1L), 15L))
        high <- bitwShiftR(high, 1L)
        if (odd) {
          high <- bitwXor(high, 0xEDB8L)
          low <- bitwXor(low, 0x8320L)
        }
      }
      c(high, low)
    }, integer(2)))
  }
  hairline_state$crc_table
}

png_crc <- function(bytes) {
  table <- crc_table()
  high <- 0xFFFFL
  low <- 0xFFFFL
  for (byte in as.integer(bytes)) {
    entry <- table[bitwAnd(bitwXor(low, byte), 0xFFL) + 1L, ]
    low <- bitwXor(bitwOr(bitwShiftR(low, 8L), bitwShiftL(bitwAnd(high, 0xFFL), 8L)), entry[2])
    high <- bitwXor(bitwShiftR(high, 8L), entry[1])
  }
  high <- bitwXor(high, 0xFFFFL)
  low <- bitwXor(low, 0xFFFFL)
  as.raw(c(bitwShiftR(high, 8L), bitwAnd(high, 0xFFL), bitwShiftR(low, 8L), bitwAnd(low, 0xFFL)))
}

big_endian <- function(value, width = 4) as.raw((value %/% 256^((width - 1):0)) %% 256)

# A tEXt chunk where the text is Latin-1, iTXt (UTF-8) otherwise, as Pillow writes them for the Python package.
png_text_chunk <- function(keyword, text) {
  latin <- iconv(text, "UTF-8", "latin1", toRaw = TRUE)[[1]]
  type <- charToRaw(if (is.null(latin)) "iTXt" else "tEXt")
  data <- if (is.null(latin)) c(charToRaw(keyword), as.raw(c(0, 0, 0, 0, 0)), charToRaw(enc2utf8(text))) else
    c(charToRaw(keyword), as.raw(0), latin)
  c(big_endian(length(data)), type, data, png_crc(c(type, data)))
}

name_png <- function(path, naming) {
  bytes <- readBin(path, "raw", file.size(path))
  header_end <- 8 + 4 + 4 + 13 + 4
  chunks <- c(png_text_chunk("Title", naming[1]), png_text_chunk("Description", naming[2]))
  writeBin(c(bytes[seq_len(header_end)], chunks, bytes[(header_end + 1):length(bytes)]), path)
}

pdf_text <- function(text) {
  paste0("<FEFF", toupper(paste(iconv(text, "UTF-8", "UTF-16BE", toRaw = TRUE)[[1]], collapse = "")), ">")
}

pdf_field <- function(text, pattern) {
  found <- regmatches(text, regexpr(pattern, text, perl = TRUE, useBytes = TRUE))
  if (length(found)) found else NULL
}

printable <- function(bytes) rawToChar(bytes[bytes != as.raw(0)])

# The last cross-reference section's offset, kind and trailer entries (Size, Root, ID).
pdf_last_section <- function(bytes) {
  tail <- printable(bytes[max(1, length(bytes) - 63):length(bytes)])
  offset <- as.numeric(sub(".*startxref\\s+([0-9]+)\\s+%%EOF\\s*$", "\\1", tail, useBytes = TRUE))
  if (is.na(offset)) stop("hairline: the PDF has no readable startxref", call. = FALSE)
  classic <- identical(rawToChar(bytes[offset + 1:4]), "xref")
  end <- grepRaw(if (classic) "startxref" else "stream", bytes, offset = offset + 1)
  dictionary <- printable(bytes[(offset + 1):(end - 1)])
  size <- pdf_field(dictionary, "/Size\\s+[0-9]+")
  root <- pdf_field(dictionary, "/Root\\s+[0-9]+\\s+[0-9]+\\s+R")
  if (is.null(size) || is.null(root)) stop("hairline: the PDF trailer has no /Size or /Root", call. = FALSE)
  list(offset = offset, classic = classic, size = as.integer(sub("/Size\\s+", "", size, useBytes = TRUE)),
       root = root, id = pdf_field(dictionary, "/ID\\s*\\[[^]]*\\]"))
}

# A new Info dictionary (the figure's title and subject, nothing else) appended as an incremental update, so no byte
# of the drawn PDF moves; readers take the latest Info, which leaves out the device's producer and timestamp.
set_pdf_info <- function(path, naming) {
  bytes <- readBin(path, "raw", file.size(path))
  section <- pdf_last_section(bytes)
  number <- section$size
  fields <- if (is.null(naming)) "" else paste0("/Title ", pdf_text(naming[1]), " /Subject ", pdf_text(naming[2]), " ")
  info <- charToRaw(sprintf("\n%d 0 obj\n<< %s>>\nendobj\n", number, fields))
  info_offset <- length(bytes) + 1
  xref_offset <- length(bytes) + length(info)
  trailer <- paste(c(section$root, sprintf("/Info %d 0 R /Prev %.0f", number, section$offset), section$id),
                   collapse = " ")
  update <- if (section$classic) {
    charToRaw(sprintf("xref\n%d 1\n%010.0f 00000 n \ntrailer\n<< /Size %d %s >>\nstartxref\n%.0f\n%%%%EOF\n", number,
                      info_offset, number + 1, trailer, xref_offset))
  } else {
    entries <- c(as.raw(1), big_endian(info_offset), as.raw(c(0, 0, 1)), big_endian(xref_offset), as.raw(c(0, 0)))
    c(charToRaw(sprintf("%d 0 obj\n<< /Type /XRef /Size %d /W [1 4 2] /Index [%d 2] %s /Length %d >>\nstream\n",
                        number + 1, number + 2, number, trailer, length(entries))), entries,
      charToRaw(sprintf("\nendstream\nendobj\nstartxref\n%.0f\n%%%%EOF\n", xref_offset)))
  }
  writeBin(c(bytes, info, update), path)
}
