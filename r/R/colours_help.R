#' Colours in hairline
#'
#' hairline picks colours for you: every chart function colours its groups,
#' amounts and highlights on its own. This page shows which colour sets there
#' are, how to choose another one, and how to keep a group's colour the same
#' across a report.
#'
#' @section Which colours for which job:
#' \itemize{
#'   \item Groups (arms, units, diagnoses): a categorical palette, e.g. `hl_use(palette = "calm")`.
#'   \item Two groups (intervention, control): a pair, `hl_use(palette = "pair")`.
#'   \item A printout in grey: `"ink"`, or the palette `"deep"`.
#'   \item Amounts (counts, rates, densities): a sequential ramp, e.g. `scale_fill_hairline_c("blues")`.
#'   \item Values above and below a midpoint: a diverging ramp, `scale_fill_hairline_c("blue-coral")`.
#'   \item One group against the rest: `+ hl_highlight("Unit B")`, or `highlight =` in [hl_timeseries()].
#'   \item A single series: the accent, `hl_use(accent = "#0b6e4f")`.
#'   \item Risk of bias: the `"judgement"` set, applied by [hl_risk_of_bias()].
#' }
#'
#' @section See what there is:
#' [hl_palettes()] lists every colour set with its kind, number of colours,
#' use, and which one is active; [hl_swatches()] draws them. The six
#' categorical palettes have eight colours each: `"daylight"` (bright and
#' balanced; the default), `"bloom"` (playful, led by magenta), `"citrus"`
#' (sunny, high energy), `"lagoon"` (fresh blue-green with coral), `"calm"`
#' (subdued, for long reports) and `"deep"` (dark and light, prints in grey).
#' The purpose sets are `"pair"`, `"pair-teal"` and `"pair-violet"` for two
#' groups, `"ink"` for greyscale print and `"judgement"` for low, some
#' concerns and high. The ramps are `"blues"`, `"teals"`, `"oranges"`,
#' `"berries"` and `"greys"` (sequential) and `"blue-coral"` and
#' `"teal-berry"` (diverging).
#'
#' @section Colour by count:
#' The number of groups decides the colours, the same in every chart: two
#' groups take the first two colours, three groups the first three. The first
#' two, three and four colours of each palette are its most readable sets of
#' that size, for colour-blind readers too, and because the sets are nested a
#' group keeps its colour when more groups are shown. A ninth group is an
#' error, not a repeated colour: fold small groups into "Other" or split the
#' figure into panels.
#'
#' @section Colour follows the name:
#' Within a session a group keeps the colour it got first, in every later
#' chart. Pin colours to names with `hl_use(colors = c("Unit B" = "#e8a628"))`
#' and read them back with [hl_color()] and [hl_colors()]. For colours that
#' stay the same across a report whatever order the charts are drawn in, put
#' them in the brand file under `defaults: hairline: colors:`; `groups:` gives
#' the units of a section tints of the section's colour.
#'
#' @section Brand and your own colours:
#' A `_brand.yml` file holds an institution's palette (`defaults: hairline:
#' categorical:`), found from the working directory upwards or given with
#' `hl_use(brand = )`; several files layer from institution to project, and
#' [hl_brand_report()] shows what was taken and which layer each colour came
#' from. While a brand is active, its ramps `"brand-sequential"` and
#' `"brand-diverging"` (from its `sequential:` and `diverging:` colours, else
#' its first one and two colours) are the default for [hl_ramp()], the
#' continuous scales and the correlation heatmap. Any vector of hex colours can be
#' a palette; [hl_check_palette()] measures how far apart the colours are for
#' colour-blind readers and everyone else, and their contrast with the
#' background (`pairs = "all"` for scatter plots and small multiples).
#'
#' @section Light colours and dark backgrounds:
#' Colours below 3:1 contrast on white stay as they are for bars and areas;
#' lines in them are drawn a little wider and points are filled with a darker
#' shade of the same hue. With `hl_use(scheme = "dark")` the background, text
#' and grid greys turn dark; data colours stay, and thin marks are shaded
#' lighter where needed. Text never takes a data colour.
#'
#' @name hairline_colours
#' @aliases hairline_colors
#' @seealso [hl_palettes()], [hl_swatches()], [hl_palette()], [hl_ramp()], [hl_use()], [hl_check_palette()].
#' @examples
#' hl_palettes("categorical")
#' hl_palette("pair")
#' hl_swatches(c("daylight", "calm", "pair", "blues"))
NULL
