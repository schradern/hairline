# Conversions between hex, sRGB, OKLab and OKLCH (Ottosson 2020), mirroring the Python package.

parse_hex <- function(color) {
  if (!is.character(color) || length(color) != 1 || !grepl("^#[0-9a-fA-F]{6}$", color)) {
    stop(sprintf("hairline: '%s' is not a 6-digit hex colour (expected '#rrggbb')", paste(color)),
         call. = FALSE)
  }
  strtoi(substring(color, c(2, 4, 6), c(3, 5, 7)), base = 16L) / 255
}

to_linear <- function(channel) {
  ifelse(channel <= 0.04045, channel / 12.92, ((channel + 0.055) / 1.055)^2.4)
}

to_gamma <- function(channel) {
  ifelse(channel <= 0.0031308, 12.92 * channel, 1.055 * channel^(1 / 2.4) - 0.055)
}

linear_to_hex <- function(linear) {
  values <- round(to_gamma(pmin(1, pmax(0, linear))) * 255)
  paste0("#", paste(sprintf("%02x", as.integer(values)), collapse = ""))
}

cube_root <- function(x) sign(x) * abs(x)^(1 / 3)

linear_to_oklab <- function(linear) {
  lms <- cube_root(matrix(c(0.4122214708, 0.5363325363, 0.0514459929,
                            0.2119034982, 0.6806995451, 0.1073969566,
                            0.0883024619, 0.2817188376, 0.6299787005), 3, byrow = TRUE) %*% linear)
  as.vector(matrix(c(0.2104542553, 0.7936177850, -0.0040720468,
                     1.9779984951, -2.4285922050, 0.4505937099,
                     0.0259040371, 0.7827717662, -0.8086757660), 3, byrow = TRUE) %*% lms)
}

oklab_to_linear <- function(lab) {
  lms <- as.vector(matrix(c(1, 0.3963377774, 0.2158037573,
                            1, -0.1055613458, -0.0638541728,
                            1, -0.0894841775, -1.2914855480), 3, byrow = TRUE) %*% lab)^3
  as.vector(matrix(c(4.0767416621, -3.3077115913, 0.2309699292,
                     -1.2684380046, 2.6097574011, -0.3413193965,
                     -0.0041960863, -0.7034186147, 1.7076147010), 3, byrow = TRUE) %*% lms)
}

hex_to_linear <- function(color) to_linear(parse_hex(color))

hex_to_oklab <- function(color) linear_to_oklab(hex_to_linear(color))

hex_to_oklch <- function(color) {
  lab <- hex_to_oklab(color)
  chroma <- sqrt(lab[2]^2 + lab[3]^2)
  hue <- if (chroma > 1e-9) (atan2(lab[3], lab[2]) * 180 / pi) %% 360 else 0
  c(lab[1], chroma, hue)
}

oklch_to_linear <- function(lightness, chroma, hue) {
  radians <- hue * pi / 180
  oklab_to_linear(c(lightness, chroma * cos(radians), chroma * sin(radians)))
}

in_gamut <- function(linear) all(linear >= -1e-6 & linear <= 1 + 1e-6)

oklch_to_hex <- function(lightness, chroma, hue) {
  linear <- oklch_to_linear(lightness, chroma, hue)
  if (!in_gamut(linear)) {
    low <- 0
    high <- chroma
    for (iteration in seq_len(40)) {
      middle <- (low + high) / 2
      if (in_gamut(oklch_to_linear(lightness, middle, hue))) low <- middle else high <- middle
    }
    linear <- oklch_to_linear(lightness, low, hue)
  }
  linear_to_hex(linear)
}
