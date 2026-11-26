# The description of a scatter plot for its alt text: each panel's linear fit with the n, r and slope its header
# writes, or with no fit, how many points it draws. Mirrors the Python package's charts/scatter_alt.py.

# "n = 120, r = 0.62, slope 0.31" from a panel header's numbers (n, r and slope, as written). As Python's fit_text().
scatter_fit_text <- function(stats) word("fit_stats", n = stats[[1]], r = stats[[2]], slope = stats[[3]])

# One fit on its own, or the first `alt_text.max_series` panels' fits by name and how many more (`fits`: a list of
# list(panel, stats), panel NULL without facets). As Python's fits_text().
scatter_fits_text <- function(fits) {
  if (length(fits) == 1 && is.null(fits[[1]]$panel)) return(word("fit_one", stats = scatter_fit_text(fits[[1]]$stats)))
  most <- hl_tokens()$alt_text$max_series
  shown <- vapply(utils::head(fits, most), function(fit) {
    word("fit_panel", panel = fit$panel, stats = scatter_fit_text(fit$stats))
  }, "")
  left <- length(fits) - most
  more <- if (left == 1) word("more_panels_one") else if (left > 1) word("more_panels_many", n = left)
  paste(c(word("fit_panels", fits = paste(shown, collapse = "; ")), more), collapse = " ")
}

# "Scatter plot. Linear fit: n = 120, r = 0.62, slope 0.31." with a fit (per panel when faceted, the panel's name
# first), else "Scatter plot. 120 points.". As Python's scatter_description().
scatter_description <- function(fits, points) {
  if (length(fits)) return(alt_described("kind_scatter", scatter_fits_text(fits)))
  counted <- if (points == 1) word("points_one") else word("points_many", n = hl_format_number(points, 0))
  alt_described("kind_scatter", counted)
}
