# Changelog

## Unreleased

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

## 0.1.0

* First release.
