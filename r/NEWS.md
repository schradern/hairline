# hairline (development version)

* `scale_y_hairline()` and `scale_x_hairline()` take `digits`, the decimals of the values a reader looks up in
  interactive output. A power of 89.6 % no longer shows as 90 % beside a 90 % target. Without `digits`
  tooltips follow the shared digits rule as before; axis labels are unchanged.

## Fixes from a stress test

* Numbers keep their exact value at any size: 1,000,000,000 no longer prints as 1,000,000,001, and 1,234.499999
  rounds to 1,234. The float tolerance no longer grows with the number.
* Nested donuts and partitions match children by their whole path, so a label repeated under two parents
  ("Other", "Shared") no longer counts its children twice.
* `hl_kaplan_meier(order = ...)` and `hl_survival()` test only the groups they draw; a group left out of `order`
  is no longer part of the log-rank p. Groups without a single event draw without a test instead of failing.
* Study endpoints read factor columns by their labels: follow-up `factor(c("10", "20"))` is 10 and 20, not the
  level codes 1 and 2.
* `hl_save()` writes every format before it replaces anything: a failed format, or a folder in the way, leaves
  existing files as they were, and a failed move is an error rather than a warning.
* `hl_effects(digits = )` reaches the forest plot as well as the table.
* `hl_over_time()` refuses date text with trailing characters and keeps clock times (2025-01-01 10:00) instead
  of cutting them to the date.
* Rolling means skip missing values inside the window, as in the Python package, and refuse windows below 1.
* Bar sums leave missing values out, as in the Python package; percent bars refuse a category that totals zero.
* The forest plot and dot plot refuse a table that leaves no room for the intervals, instead of drawing the axis
  backwards; the error names the room needed.
* A data column named `Count` stays a column when rows are counted (the count becomes `Rows`).
* HTML embeds the font the plot was drawn with: the installed files of a custom font, the bundled files only for
  Hairline Sans. Tooltips keep the locale the plot was made in.
* TIFF files carry the figure's title and description, as the other formats do.
* `hl_raincloud()` leaves missing values out and draws one group with `comparisons = "all"`.
* Clear errors for inputs without a defined result: PRISMA counts that are negative or fractional, standard
  errors of zero or less, an interval with only one end, repeated risk-of-bias judgements, a linear fit without
  two x values, a constant column in a correlation, missing follow-up times. Rank tests on all-equal values read
  "p not defined".

# hairline 0.1.0

* First release.
* One frame for titles, legends, panels and captions around any ggplot (`theme_hairline()`), with the
  type scale, spacing and line widths of the shared design tokens.
* Nineteen charts, from bars and time series to Kaplan-Meier, forest, Sankey and PRISMA diagrams.
* `hl_study()` with endpoints for cohort description, group comparison, effects, survival and change over
  time; each returns a figure, a table, values and a sentence.
* Brands in the 'brand.yml' format, entity colours pinned to names, colour-vision checked palettes, light
  and dark schemes.
* `hl_save()` for PDF, PNG, TIFF, SVG and interactive HTML; files are named by the figure and carry no
  timestamps.
* Output matches the 'hairline' Python package.
