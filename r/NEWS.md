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

## Fixes from a second stress test

* Numbers are rounded in decimal from the 15 significant digits a double holds: 999,999,999,999,999.4 stays
  999,999,999,999,999, and the stored 8.645 is a half. A missing number reads "–", an infinite one "∞".
* Decimals follow the data's spread as well as its size, so 0.0004 and 1000.2 ± 0.1 keep their digits in tables,
  key numbers and tooltips. A median between two small whole numbers keeps its half (2.5, not 3). Bar, flow and
  donut labels keep the data's decimals (0.12, not 0), slopes show two significant digits, survival medians gain
  decimals for short times, and forest and dot plots show small estimates with the digits they need.
* The Kaplan–Meier median on a flat 50 % is the middle of the flat, as survival::survfit takes it. The log-rank
  test, as survival::survdiff, uses only groups with expected events and is left out (no p) where it is undefined
  instead of failing.
* A missing group label, an `order` naming no group, empty data, text where numbers belong, and values a chart
  cannot draw (an estimate outside its interval, a self-flow, negative arc values) each give a message that names
  the column and row.
* Flow charts skip missing values like bars and donuts; an arc carries both directions of a pair (A ↔ B) instead
  of two arcs drawn on top of each other. A real "Other" joins the folded "Other" slice.
* Factor levels set the group order in every chart. Scatter fits cover the groups drawn.
* Ridgelines show a group too small or uniform for a density as spikes. Egger's test needs three studies with
  different standard errors and reads "p not defined" otherwise.
* Dates in study data are left out of tables (follow them with `hl_over_time()`). Unknown columns, empty studies and
  unknown types are named.
* Saving checks sizes and resolution, reads formats in any case and each once.
* Date tooltips keep the data's time zone and show the clock time for intraday data.
* Figures fitted to their content keep the room for labels turned upright.
* ISO times with a zone (2025-01-01T10:00Z, +01:00) are read; `hl_timeseries()` reads ISO date text as dates. The
  period mean ignores missing values. `hl_study(types = c(...))` works with a named vector.
* `hl_save()` and `hl_layout_report()` refuse sizes and resolutions of zero or less, which crashed R in ragg.
  `hl_use()` refuses sizes of zero or less and empty palettes. `hl_format_number()` formats one number.
* Models with aliased terms leave those out with a warning; a Kaplan–Meier fit without intervals draws its curves.

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
