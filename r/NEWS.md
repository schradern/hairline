# hairline (development version)

## Long labels

* Long labels wrap instead of running off the figure, by one rule in every chart: a label keeps one line while the
  chart keeps its minimum size, and otherwise wraps into the room that size leaves. `hl_donut()` and `hl_chord()`
  labels wrap beside a ring of the minimum radius, `hl_venn()` set names beside circles of the minimum radius,
  `hl_risk_of_bias()` domains (and the `overall` row) beside bars of `risk_of_bias.min_plot`, `hl_sankey()`
  labels beside links of `sankey.min_plot` (new tokens), and the `favours` labels of `hl_forest()` between the
  null line and the panel's edge. A value that no longer fits after the last line takes a line of its own.
* A word wider than its room is an error that names the label, the room it needs and the room the figure leaves,
  as the forest and spread layouts do.
* The donut's `total_label` wraps inside the hole, and is refused with the hole's width when a word does not fit.
* Labels taller than the panel grow the figure instead of piling up: a Sankey diagram keeps a line of height per
  node on average and a gap between nodes that holds the tallest label (40 sources at 120 mm lost a node above the
  panel), a nested donut's key starts at the top of the panel and runs on below it (80 children started at
  y = -455 pt), and donut, chord and Venn labels that need more height than the panel make it taller. These charts
  never shrink: at normal widths they keep the size they had.

## Fixes from the 0.2.0 stress test

* Study endpoints with more groups than the palette has colours (nine groups on an eight-slot palette), or a
  categorical variable with more categories than that, return their table, values and text with `figure = NULL`
  and a warning that says why, instead of failing. `hl_describe()`, `hl_compare()`, `hl_distribution()`,
  `hl_survival()` and `hl_over_time()` follow the same rule.
* `hl_survival()`, `hl_kaplan_meier()` and the log-rank test count the number at risk, events and deaths per
  group from sorted times at once instead of rescanning every row at every time: 100,000 rows take a fraction of a
  second instead of about 85 seconds. Results are unchanged and match `survival::survdiff()` and
  `survival::survfit()`.
* Saving a chart with many points checks each distinct colour for the light-slot treatment once instead of once
  per point: a Kaplan–Meier figure of 100,000 rows saves about five times faster.
* Values too small to show within six decimals keep two significant digits: a median near 1e-9 reads
  0.0000000012 in tables, texts, spread key numbers, tooltips and axis labels, not 0.000000. Float noise is snapped
  away relative to the value, so values near 1e-11 keep their digits too.
* `hl_save()` refuses a figure whose frame cannot be laid out with an error of class `hairline_layout_error`, as the
  Python package raises `HairlineLayoutError`, instead of saving the plot without the hairline frame. Drawing
  through ggplot2 itself (printing, `ggsave()`, a viewer window that can still be resized) keeps the fallback and
  its warning.
* Brand files follow one rule for the shape of every section hairline reads: `color`, `color.palette`,
  `typography`, `defaults.hairline`, its `colors`, `groups`, `sizes` and `outputs`, and `meta` are mappings; a list
  (`typography.fonts`, `categorical`, a group's members) may be written as its single value
  (`categorical: harbor`); each font entry is a mapping. Anything else is an error naming the file, the key and
  what it holds, instead of "$ operator is invalid for atomic vectors" or a list taken as a palette. A key given
  twice reads "key 'harbor' is given twice".
* `hl_save()` refuses a dpi below 20, at which text is smaller than a pixel.
* A bar whose values are all missing draws no bar, no value label and no tooltip, instead of a bar labelled 0.
  For sorting and percent totals it counts as zero, as before.
* Study texts count one row in the singular: "1 participant", "1 row repeats an id", "1 value is infinite",
  "1 variable". `hl_study(unit = ...)` takes a plural noun, whose singular drops a final s, or a singular and plural
  pair such as `c("mouse", "mice")`.
* `hl_use(output = ...)` refuses an unknown export type with `brand = FALSE` too.
## Narrow figures (one column of a two-column page)

* Plots with axes keep their plot room: when the title, legend, panel headers, axis or table would squeeze the
  panels below `spacing.min_plot_height` (8 x the base size, for all panel rows together, each row at least
  `min_panel_height`), `hl_save()` (and `hl_layout_report()`, host hand-off, HTML) makes the figure taller instead
  of failing with "figure too small". `hl_scatter(by =)` and `hl_timeseries()` at 75 mm (`width_mm` from a host
  context) used to fail. Figures with room to spare keep their size (the gallery is unchanged). It replaces the
  Kaplan–Meier-only rule and the `survival.min_plot` token. A chart can ask for more room
  (`plot@meta$hairline_min_plot`): `hl_raincloud()` does, by its bracket levels, and the study overview asks for
  less (`study.overview_min_row` per group row), as its strip is sized from its rows. A plot printed to a device of
  fixed size keeps that size; "figure too small" then names the height that fits: "make it at least 52 mm tall
  (hl_save(height_mm = 52))".
* `hl_timeseries()` plots are saved at the `"double"` size (174 mm) by default, as in the Python package, where
  they were 120 mm wide: `hl_save()`, `hl_layout_report()` and the host hand-off take `size = NULL`, the plot's own
  size (`"onehalf"` for every other plot).
* `hl_bars()` lies down when its category names, or the values over its bars, are too wide for upright bars at
  the figure's width (`bars.label_space` x the base size between neighbours), not only by label count and length:
  seven or eight department names collided at 85 mm, and eight already did at 120 mm. The new `size` argument
  names the size the bars are laid out for (the host's column, else the preset's width), as `size=` does in
  Python, and becomes the plot's own size for `hl_save()`.
* `hl_raincloud()` comparison brackets keep room for their p labels: a short plot grows until every bracket level
  is taller than its label, instead of stacking the labels into the brackets above.
* `hl_scatter()` draws points at the axis limits whole (`coord_cartesian(clip = "off")`); limits end on a break,
  so the panel edge cut them in half.
* Numbers from 10^9 on are written in one short-scale unit per axis and per bar chart (`1.25 tn`, `0.8 tn`;
  German `Bio.`, `Mrd.`), with the tick step's decimals on axes and `numbers.compact_digits` on bars, instead of
  thirteen digits that ran past the bars and the figure. Tooltips keep the full number.

# hairline 0.2.0

* Study results carry `numbers`: the unrounded quantities their table, values and text are formatted from. Per
  group n and the median and quartiles, mean and SD, range, or counts and shares; for a test its method,
  statistic, degrees of freedom where defined and p (`NA` when undefined); for survival n, events, medians and
  the log-rank test; for effects the estimates, intervals, scale (ratio or difference) and, for `lm`, `glm` and
  `coxph` models, the reference level of each treatment-coded factor.
* Every study result counts the rows it analysed and those left out because the variable, group or date was
  missing, overall and per group, and its text says so when rows were left out: "82 of 100 patients; 18 without
  a value were left out." `hl_describe()` names the variables with missing values; rows without a group are
  counted in Overall only, and the text says how many.
* With `id =`, `hl_describe()`, `hl_compare()` and `hl_distribution()` refuse a variable with more than one row
  per id instead of counting repeated measurements as separate patients; the error names the id column and the
  most rows per id, and points to one row per id or to `hl_over_time()`.
* Rows in groups that `order =` leaves out are counted (`other_groups`) and named in the text, so the analysed
  count is exact when `order` selects groups.

## Fixes from a second external review

* `hl_study(order = ...)` refuses a group named twice, which analysed the same rows as two samples
  (Kruskal–Wallis on three samples instead of the rank-sum test on two).
* A variable named like the column the endpoints add for the group (`.group`) no longer breaks `hl_compare()` and
  `hl_distribution()`; the internal name never collides with a data column.
* A group called "Overall" keeps its own column in `hl_describe()`; the aggregate is then "Overall (all)".
* A group column without a single value, or an `order` that names none of its groups, is a study error that the
  endpoints name. `hl_compare()` and `hl_over_time()` refuse a variable with no value in any group.
* `stats = character()` is refused with a clear message.
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

## Fixes from a third review

* `lm` models in the forest plot keep their own Student-t intervals (as `confint()`); glm and coxph keep their
  Wald intervals.
* A group named twice in `order` is refused instead of entering the analysis twice.
* `hl_timeseries()` keeps data columns named `.mean`, `.group`, `.x` or `.y` as they are.
* Labels holding a carriage return no longer merge with other labels.
* Negative bars keep their sign in HTML tooltips and have proper hover targets; interactive lines break where the
  static line breaks.
* A survfit with delayed entry draws without a number-at-risk table, with a warning: it keeps no entry times, so
  the counts between its times are unknown.
* `hl_save()` names its temporary files so they never meet existing ones.
* Tooltips show seconds when the times have them; impossible zone offsets (+99:99) are refused.

## Fixes from a fourth review

* A group left out of `order` no longer adds its categories to a comparison's table: they changed the
  chi-squared test's degrees of freedom and p-value although none of the group's rows were analysed.
* A 2 x 2 table with an expected count below 5 is tested with Fisher's exact test instead of chi-squared.
* With `id =` set, every endpoint that counts patients (`hl_describe()`, `hl_compare()`, `hl_distribution()`,
  `hl_survival()`) refuses an id with more than one row, wherever its values are missing.
* The rank-sum p keeps far tails in either order of the groups; `wilcox.test()` returned 0 for one order.
* The SD of a single value is undefined and reads "–" (it read 0.0).
* `hl_compare()` keeps a decimal for quartiles of small whole numbers, as `hl_distribution()` does.
* `$values` of `hl_compare()`, `hl_distribution()` and `hl_survival()` holds the group summaries under
  `groups`, beside `test` and `p`, so a group named "test" or "p" no longer collides with them.
* The README installs the package from GitHub (it is not on CRAN yet); the version is now 0.1.0.9000.

## Fixes from the pre-release stress test

* A host context file that is missing or broken no longer breaks every `hl_save()` ("$ operator is invalid for
  atomic vectors"): the warning said "continuing without it", and now it does.
* Charts that fit their height to their content measure on a device whose resolution drops for very large
  figures, so its buffer stays small; it grew with the square of the width (a 100 m width filled the machine).
* A PNG or TIFF beyond 600 megapixels (about an A0 poster at 600 dpi; token `export$max_megapixels`) is refused
  before its buffer is allocated, with the size and dpi that asked for it.
* An `hl_use()` call that fails (a base size of 0, an unknown palette) no longer comes back with every new host
  context: its arguments are kept for re-applying only once they have been applied. Every later plot in the
  session failed with the first call's error.
* A host context whose `width_mm`, `base_size` or `dpi` is not a number above zero warns once and leaves that
  value out.

* The bundled font is registered when the package loads: without `hl_use()`, plots were measured and drawn in a
  system font (Helvetica on macOS) and their layout differed from the Python package's.
* A host context is applied without stopping anything: a `locale` like "de-DE" is read as "de", one hairline
  lacks ("fr") warns and is left out (it stopped `library(hairline)`); a style that cannot be applied (a broken
  `_brand.yml`) warns instead of failing to load; a context file that holds a JSON array, a `figure_dir` or
  `design` of the wrong kind warn and are left out. The first plot after a new context already has its style,
  and a damaged `hairline-figures.json` is replaced with a warning instead of failing every save.
* `hl_use(background = ...)` refuses a value that is no colour; a brand's `base_size` must be a number above
  zero; `hl_save()` checks the size preset first ("unknown size") and refuses an empty name. Brand errors about a
  value YAML read as empty (an unquoted `#hex` is a comment) say "null" instead of having no message.
* Infinite values are refused with the column and row in every chart that reads numbers (`hl_donut()`,
  `hl_partition()`, `hl_sankey()`, `hl_chord()`, `hl_arcs()`, `hl_correlation()`, `hl_kaplan_meier()`,
  `hl_spread()`, `hl_scatter()`, `hl_bars()`, `hl_timeseries()`, PRISMA counts, `hl_spread()` marks). Text in a
  number column of `hl_bars()`, `hl_timeseries()`, `hl_scatter()` or `hl_correlation()` gets the "needs numbers"
  message.
* Clear messages instead of internal errors for empty data (`hl_donut()`, `hl_partition()`, `hl_bars()`), an
  empty `order` (now: no order), `hl_kaplan_meier()` without time and event columns, `hl_risk_of_bias()` without
  domain and judgement columns, `hl_swatches(character())`, `hl_funnel(pooled = NaN)` and standard errors so
  large that a ratio funnel passes 1e±10, `hl_spread()` marks for groups that are not drawn, a statistic named
  twice or fractional `digits`, timeseries events that are not dates on a date or time axis (a POSIXct axis
  failed on every event), and `hl_bars(percent = TRUE)` with negative values.
* `hl_bars()` and `hl_scatter()` without `by` draw no legend swatch (an empty one took a legend row, and made a
  scatter at 75 mm too small to draw).
* Labels that leave a panel less than 2 x the base size (token `spacing$min_panel_width`) are refused, "figure
  too narrow". `hl_dotplot()` and `hl_forest()` keep their row pitch and the figure grows to hold every row.
* Study: `order` without `group` is refused; numeric `order` values name groups as text; values of a numeric
  variable that are no numbers or infinite are study errors; infinite follow-up times are refused;
  `hl_compare()` keeps a factor's level order (it sorted the levels alphabetically); `hl_distribution()` draws
  the groups that have values; `hl_effects()` refuses a term named twice; a variable named twice is refused
  (it failed with "factor level is duplicated"). Numeric levels read the same in both languages (1e-04 reads
  0.0001, -0 reads 0). Titles and sentences use the group's label and keep acronyms ("Median PFS").

## Fixes for narrow figures and installed fonts

* `hl_forest()` and `hl_dotplot()` fit one column of a two-column page (75 mm): when the columns beside the intervals
  (effect, weight, extra columns) would leave the plot less than `forest$min_plot`, they move to a line under each
  study, aligned in columns under a two-line heading, as `hl_spread()` does with its numbers. A 5-study forest failed
  at 75 and 85 mm; one too narrow even for that is refused with the room it needs.
* `hl_kaplan_meier()` grows the figure when its frame (title, legend, header, axis, number-at-risk table) would leave
  the curves less than 8 x the base size high (token `survival$min_plot`): at 75 and 85 mm the curves had -7 and
  13 pt and the figure failed. Wider figures keep their size.
* `hl_spread()` keeps its plot on a narrow figure. The key numbers sit beside the plot while it keeps at least
  8 × the base size (token `spread$min_plot`, as the forest plot has); on a narrower figure, such as one column of
  a two-column page (75 mm), they move to a line under each row, so no statistic is dropped. The plot had shrunk
  to nothing and its axis ran backwards, the tick labels piled on one another. A figure too narrow even for that
  is refused with the room it needs. Rows keep their pitch and the figure grows to hold them, instead of rows
  squeezed into the default height; `stats = character()` draws the plot to the right edge instead of failing.
* Text is measured and drawn in a weight the font has: a requested weight resolves to the nearest face of the
  family, as browsers match fonts (600 of a family with 400 and 700 is 700), as the Python package does. HTML
  output embeds the faces actually drawn.

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
