# Changelog

## Unreleased

### Long labels

* Long labels wrap instead of running off the figure, by one rule in every chart: a label keeps one line while the
  chart keeps its minimum size, and otherwise wraps into the room that size leaves. Donut and chord labels wrap
  beside a ring of the minimum radius, Venn set names beside circles of the minimum radius, risk-of-bias domains
  (and the `overall` row) beside bars of `risk_of_bias.min_plot`, Sankey labels beside links of `sankey.min_plot`
  (new tokens), and the forest plot's `favours` labels between the null line and the panel's edge. A value that no
  longer fits after the last line takes a line of its own.
* A word wider than its room is a `HairlineLayoutError` that names the label, the room it needs and the room the
  figure leaves, as the forest and spread layouts do.
* The donut's `total_label` wraps inside the hole, and is refused with the hole's width when a word does not fit.
* Labels taller than the panel grow the figure instead of piling up: a Sankey diagram keeps a line of height per
  node on average and a gap between nodes that holds the tallest label (40 sources at 120 mm lost a node above the
  panel), a nested donut's key starts at the top of the panel and runs on below it (80 children started at
  y = -455 pt), and donut, chord and Venn labels that need more height than the panel make it taller. These charts
  never shrink: at normal widths they keep the size they had.

## 0.2.0

* Study results carry `numbers`: the unrounded quantities their table, values and text are formatted from. Per
  group n and the median and quartiles, mean and SD, range, or counts and shares; for a test its method,
  statistic, degrees of freedom where defined and p (NaN when undefined); for survival n, events, medians and the
  log-rank test; for effects the estimates, intervals, scale (ratio or difference) and, for formula models, the
  reference level of each factor.
* Every study result counts the rows it analysed and those left out because the variable, group or date was
  missing, overall and per group, and its text says so when rows were left out: "82 of 100 patients; 18 without
  a value were left out." `describe()` names the variables with missing values; rows without a group are counted
  in Overall only, and the text says how many.
* With `id=`, `describe()`, `compare()` and `distribution()` refuse a variable with more than one row per id
  instead of counting repeated measurements as separate patients; the error names the id column and the most
  rows per id, and points to one row per id or to `over_time()`.
* Rows in groups that `order=` leaves out are counted (`other_groups`) and named in the text, so the analysed
  count is exact when `order` selects groups.

### Fixes from a second external review

* `study(order=...)` refuses a group named twice, which analysed the same rows as two samples (Kruskal–Wallis on
  three samples instead of the rank-sum test on two).
* A variable named like the column the endpoints add for the group (`_group`) no longer breaks `compare()` and
  `distribution()`; the internal name never collides with a data column.
* A group called "Overall" keeps its own column in `describe()`; the aggregate is then "Overall (all)".
* A group column without a single value, or an `order` that names none of its groups, is a study error that the
  endpoints name, instead of an `IndexError`. `compare()` and `over_time()` refuse a variable with no value in any
  group.
* `stats=[]` is refused with a clear message.
* `HairlineFigure.percent_axis()` takes `digits`, and the new `HairlineFigure.number_axis()` does the same for
  plain numbers: the decimals of the values a reader looks up in interactive output. A power of 89.6 % no longer
  shows as 90 % beside a 90 % target. Without `digits` tooltips follow the shared digits rule as before; ticks
  are unchanged.
* `import hairline` no longer loads pandas. Chart and study functions load on first use, so a figure drawn with
  `figure()` and saved as SVG or HTML never imports pandas, and `import hairline` takes about 40 % less time.

### Fixes from a stress test

* Numbers keep their exact value at any size: 1,000,000,000 no longer prints as 1,000,000,001, and 1,234.499999
  rounds to 1,234. The float tolerance no longer grows with the number.
* Nested donuts and partitions match children by their whole path, so a label repeated under two parents
  ("Other", "Shared") no longer counts its children twice.
* `kaplan_meier(order=...)` and `study.survival()` test only the groups they draw; a group left out of `order`
  is no longer part of the log-rank p. Groups without a single event draw without a test instead of failing,
  and missing follow-up times are refused.
* `save()` writes every format before it replaces anything: a failed format, or a folder in the way, leaves
  existing files as they were.
* Stacked bars put negative segments below zero, as the R package does, with the signed total past the positive
  segments. Percent bars refuse a category that totals zero.
* The forest plot and dot plot refuse a table that leaves no room for the intervals, instead of drawing the axis
  backwards; the error names the room needed.
* A data column named `Count` stays a column when rows are counted (the count becomes `Rows`).
* HTML embeds the font the figure was drawn with: the installed files of a custom font, the bundled files only
  for Hairline Sans. Tooltips keep the locale the figure was made in.
* TIFF files carry the figure's title and description, as the other formats do.
* `spread()`, `timeseries()` and the other grouped charts find numeric groups from text `order` (`["1", "2"]`).
* `share_above` leaves missing values out of its denominator; `raincloud()` leaves them out of the cloud and its
  n; `describe()` keeps its overview when one group has no values; Venn diagrams count iterators like lists.
* Clear errors for inputs without a defined result: rolling windows below 1, PRISMA counts that are negative or
  fractional, standard errors of zero or less, an interval with only one end, repeated risk-of-bias judgements, a
  linear fit without two x values, a constant column in a correlation. Rank tests on all-equal values read
  "p not defined".
* The t quantile and the chi-square tail hold at extreme degrees of freedom and probabilities.

### Fixes from a second stress test

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
* Pandas categories set the group order in every chart. Scatter fits cover the groups drawn.
* Ridgelines show a group too small or uniform for a density as spikes. Egger's test needs three studies with
  different standard errors and reads "p not defined" otherwise.
* Dates in study data are left out of tables (follow them with `over_time()`). Unknown columns, empty studies and
  unknown types are named.
* Saving checks sizes and resolution, reads formats in any case and each once.
* Date tooltips keep the data's time zone and show the clock time for intraday data.
* Figures fitted to their content keep the room for labels turned upright.
* `save()` takes any background colour, saves through a link to its target and keeps short temporary names. A
  drawing error raises instead of leaving a blank figure. `use()` refuses sizes of zero or less and empty palettes.
* Greek letters (α, β, Δ, χ) fall back to DejaVu Sans, glyph by glyph; the bundled font has none.
* `km_estimate()` is vectorised: 50,000 rows take milliseconds instead of seconds.

### Fixes from a third review

* Models fitted from arrays (statsmodels OLS or PHReg without pandas) reach the forest plot, their terms named
  from the model.
* A group named twice in `order` is refused instead of entering the analysis twice.
* Labels that read the same as text (1 and "1") are refused instead of merging their groups.
* Negative bars have proper hover targets in HTML.
* A Kaplan–Meier fit with delayed entry counts only those who have entered in the number at risk; weighted fits
  keep fractional counts.
* Tooltips show seconds when the times have them; ISO text with mixed zone offsets reads in UTC.

### Fixes from a fourth review

* A group left out of `order` no longer adds its categories to a comparison's table: they changed the
  χ² test's degrees of freedom and p-value although none of the group's rows were analysed.
* A 2 × 2 table with an expected count below 5 is tested with Fisher's exact test instead of χ².
* With `id=` set, every endpoint that counts patients (`describe`, `compare`, `distribution`, `survival`)
  refuses an id with more than one row, wherever its values are missing: counts and events take every row.
* The rank-sum p keeps far tails in either order of the groups (it was 0 for one order).
* The SD of a single value is undefined and reads "–" (it read 0.0).
* `compare()` keeps a decimal for quartiles of small whole numbers, as `distribution()` does.
* `.values` of `compare()`, `distribution()` and `survival()` holds the group summaries under `"groups"`,
  beside `"test"` and `"p"`, so a group named "test" or "p" no longer overwrites the test or loses its summary.
* `over_time()` reads ISO times across a clock change (mixed offsets) in UTC.
* The README installs the development version from GitHub; the version is now 0.2.0.dev0, so a checkout is
  told apart from the 0.1.0 release on PyPI.

### Fixes from the pre-release stress test

* Charts that fit their height to their content (`spread`, `forest`, `dotplot`, `correlation`, `arcs`,
  `partition`, `prisma`, `risk_of_bias`) no longer draw the provisional figure as pixels to measure it. Its memory
  grew with the square of the width: 2.8 GB at 4 m, and a 100 m host width filled the machine. Only the frame is
  laid out now, in pt, which is also faster.
* A PNG or TIFF beyond 600 megapixels (about an A0 poster at 600 dpi; token `export.max_megapixels`) is refused
  before its buffer is allocated, by `save()` and by `savefig()` on a hairline figure, with the size and dpi that
  asked for it. matplotlib no longer limits raster sizes itself.
* A `use()` call that fails (a base size of 0, an unknown palette) no longer comes back with every new host
  context: its arguments are kept for re-applying only once they have been applied. Every later figure in the
  session failed with the first call's error.
* A host context whose `width_mm`, `base_size` or `dpi` is not a number above zero warns once and leaves that
  value out (it reached matplotlib as it was); an explicit `width_mm` or `height_mm` of 0 or less is refused, as
  in R, instead of falling back to the preset or failing inside matplotlib.

* A host context is applied without stopping anything: a `locale` like "de-DE" is read as "de", one hairline
  lacks ("fr") warns and is left out (it stopped `import hairline`); a style that cannot be applied (a broken
  `_brand.yml`) warns instead of failing the import; `figure_dir` and `design` of the wrong kind warn and are
  left out; `interactive: "false"` no longer turns HTML on. The first figure after a new context already has its
  style (it had the previous one), and a damaged `hairline-figures.json` is replaced with a warning instead of
  failing every save.
* `use(background=...)` refuses a value that is no colour (it stayed in the session and failed every later
  figure); a brand's `base_size` must be a number above zero; `save()` refuses an empty name.
* Infinite values are refused with the column and row in every chart that reads numbers (`donut`, `partition`,
  `sankey`, `chord`, `arcs`, `correlation`, `kaplan_meier`, `spread`, `scatter`, `bars`, `timeseries`, PRISMA
  counts, `spread` marks): they crashed or drew NaN shapes. Text in a number column of `bars`, `timeseries`,
  `scatter` or `correlation` gets the "needs numbers" message the other charts give.
* Clear messages instead of internal errors: `kaplan_meier` without time and event columns, with `stats` that are
  not (label, value) pairs, `times` that are negative, or an `order` group without a fit; `prisma` with
  `excluded_reasons` that is not a mapping; `risk_of_bias` with a missing study or domain; `donut` without a
  label column; `correlation` with two columns of one name; `raincloud` with no values; `spread` with `marks` for
  a group that is not drawn or that are not finite, a statistic named twice, or `digits` that is not a whole
  number; `funnel` on a ratio scale with standard errors so large that its limits pass ratios of 1e±10 (a model
  with separation); timeseries bands and events that are not dates on a date axis (or numbers on a number axis);
  `bars(percent=True)` with negative values (they drew -100 % and 200 %).
* An empty `order` is no order. `stats="median"` is one statistic.
* Labels that leave a panel less than 2 x the base size (token `spacing.min_panel_width`) are refused, "figure
  too narrow", as a figure too short already was: long bar labels drew the bars into nothing.
* `dotplot` and `forest` keep their row pitch and the figure grows to hold every row; with many rows the rows
  were squeezed until their labels overlapped.
* Study: `order` without `group` is refused at `study()`; numeric `order` values name groups as text
  (`order=[2, 1]`); values of a numeric variable that are no numbers ("<5") or infinite are study errors the
  endpoints name; follow-up times that are infinite are refused; a DataFrame with a repeated index and `id=` no
  longer fails; `distribution()` draws the groups that have values; `effects()` refuses a term named twice (it
  dropped one); a variable named twice is refused. Numeric levels read the same in both languages (0.1 + 0.2 and
  0.3 are one level, 1e-4 reads 0.0001, -0 reads 0). Titles and sentences use the group's label ("by treatment
  arm") and keep acronyms ("Median PFS", not "Median pfs").

### Fixes for narrow figures and installed fonts

* `forest()` and `dotplot()` fit one column of a two-column page (75 mm): when the columns beside the intervals
  (effect, weight, extra columns) would leave the plot less than `forest.min_plot`, they move to a line under each
  study, aligned in columns under a two-line heading, as `spread()` does with its numbers. A 5-study forest failed
  at 75 and 85 mm; one too narrow even for that is refused with the room it needs.
* `kaplan_meier()` grows the figure when its frame (title, legend, header, axis, number-at-risk table) would leave
  the curves less than 8 x the base size high (token `survival.min_plot`): at 75 and 85 mm the curves had -7 and
  13 pt and the figure failed. Wider figures keep their size.
* `spread()` keeps its plot on a narrow figure. The key numbers sit beside the plot while it keeps at least
  8 × the base size (token `spread.min_plot`, as the forest plot has); on a narrower figure, such as one column of
  a two-column page (75 mm), they move to a line under each row, so no statistic is dropped. The plot had shrunk
  to nothing and its axis ran backwards, the tick labels piled on one another. A figure too narrow even for that
  is refused with the room it needs. Rows keep their pitch and the figure grows to hold them, instead of rows
  squeezed into the default height; `stats=[]` draws the plot to the right edge instead of failing.
* Text is drawn in a weight the font has: a requested weight resolves to the nearest face of the family, as
  browsers match fonts (600 of a family with 400 and 700 is 700). A title in Helvetica Neue no longer makes
  matplotlib log "findfont: Failed to find font weight 600"; HTML output embeds the faces actually drawn.

## 0.1.0

* First release.
