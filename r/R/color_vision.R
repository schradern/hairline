# Colour-vision simulation (Machado, Oliveira & Fernandes 2009, severity 1.0), distance and contrast.

machado_matrix <- function(kind) {
  values <- switch(kind,
    protan = c(0.152286, 1.052583, -0.204868, 0.114503, 0.786281, 0.099216, -0.003882, -0.048116, 1.051998),
    deutan = c(0.367322, 0.860646, -0.227968, 0.280085, 0.672501, 0.047413, -0.011820, 0.042940, 0.968881),
    stop(sprintf("hairline: unknown colour-vision deficiency '%s'; use 'protan' or 'deutan'", kind), call. = FALSE)
  )
  matrix(values, 3, byrow = TRUE)
}

simulate_linear <- function(color, kind) {
  pmin(1, pmax(0, as.vector(machado_matrix(kind) %*% hex_to_linear(color))))
}

simulate_cvd <- function(color, kind) linear_to_hex(simulate_linear(color, kind))

delta_e <- function(first, second, kind = NULL) {
  if (is.null(kind)) {
    a <- hex_to_oklab(first)
    b <- hex_to_oklab(second)
  } else {
    a <- linear_to_oklab(simulate_linear(first, kind))
    b <- linear_to_oklab(simulate_linear(second, kind))
  }
  100 * sqrt(sum((a - b)^2))
}

relative_luminance <- function(color) sum(c(0.2126, 0.7152, 0.0722) * hex_to_linear(color))

contrast_ratio <- function(first, second) {
  values <- sort(c(relative_luminance(first), relative_luminance(second)), decreasing = TRUE)
  (values[1] + 0.05) / (values[2] + 0.05)
}
