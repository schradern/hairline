# Changelog

## Unreleased

### Tooltips on every chart

* `raincloud`: each group's box reads its n, every measure of `summary=` and `stats=`, and with `compare=` its Δ
  [95 % CI] and p, as the numbers under the groups; each point reads its value ("Surgical: 12.3"). Hovering a group
  keeps its density, marks and points in colour, in every `facet` panel; values cut by `clip` and groups below
  `min_n` have no tooltip.
* `ridgeline`: each ridge reads its n, its centres and the `stats=` and `compare=` numbers beside it, at its median
  line (or its peak); hovering it keeps it in colour, in every panel.
* `study().describe()`: each overview row reads its median, IQR, range and n. The other study figures were already
  covered by the charts they draw.
* `prisma`: each box reads its label and count, the exclusion box its reasons one under another; the box text stays
  in view.
* Tooltips can hold several lines. A test runs every gallery figure and fails when one exports a series without a
  tooltip, or when a chart has no gallery figure.

### Reference in the legend

* `reference_legend=True` on `bars`, `spread`, `dotplot`, `raincloud`, `ridgeline`, `scatter`, `timeseries` and
  `kaplan_meier` names the labelled reference in the legend row, as a dashed entry, instead of at its line. One
  labelled reference at most: two dashed entries look alike.

### Fixes

* With a brand of fewer categorical slots than groups, explicit `colors=` (a mapping or a ramp) now draw: only
  series that would repeat a colour are refused.
* A reference's `legend_label` joins the legend row also when the chart sets its own legend (`raincloud(summary=...)`)
  or shows none.

## 0.3.0

What two real reports needed beyond 0.2.1 (see `docs/backlog.md`): a quality report on a perioperative drug and the
staffing of a surgical unit over the day. Then two rules for every chart: nothing overlaps, and the same measures
(`summary=`, `stats=`) on every distribution chart, with differences between groups as numbers beside them
(`compare=` and `numbers=`). Existing calls keep working; a figure whose texts or marks collided now lays out
without the collision (see "Nothing overlaps" below).

### For reports

* `bars(facet=, scales=, columns=)`: one panel per facet value, each with its own value axis or one shared
  axis, the facet's total in its panel header. `top=` and `other=` keep the largest categories per panel and
  fold the rest into one bar.
* `partial=` on `bars()` and `timeseries()`: incomplete periods are drawn lighter and named in the caption, in
  the locale ("Unvollständig, heller: 2021 (2 Monate)").
* `show_n=` on `bars()`, `spread()` and `ridgeline()`, `n=` on `dotplot()`: the n after the label or in the
  numbers column, formatted in the locale; colours and `order` keep keying on the bare group.
* `min_n=` on `spread()`, `ridgeline()` and `raincloud()`, `clip=` (a quantile or `(low, high)`) and
  `clip_stats=` on those and `scatter()`: groups and values left out are counted in the caption.
* `normalize=` on `bars()`: shares from counts, the n of each category kept in its label.
* `color_by=` on every chart with groups: groups coloured by a coarser column, which the legend lists and the
  palette check counts. `dimension=` and `hl.scope()` keep the categories of one dimension off the slots another
  dimension holds, with an error naming both when the palette is full.
* `spread(stats=("levels", ...), discrete=True)`: the most frequent values with their shares, and quantiles on
  the data's own levels, each level written as given (12.5 mg, 50 mg). `spread()` and `describe()` warn when a
  median falls between two levels that each hold more than 20 % of the values.
* `table()`: any frame in hairline's typography, numbers in the locale, wrapped headings, indents kept,
  `bold_rows=` and `footnotes=`; `save()` writes it as PDF, PNG, SVG and as a real HTML `<table>`.
* `report()`: figures and tables numbered in the locale, in one self-contained Markdown or HTML file.

### Over the time of day

* `lanes()`, `levels()` and `swimlanes()`, with `days=` (weekdays, weekends, a list), `hours=`, `spans=` and
  `into=` / `panel=` to draw into a composed figure on one time axis.
* `figure(heights=, sharex=, sharey=)`: panel rows sized by content; rows with `heights` share y only when asked.
* `HairlineFigure.time_axis()`, `integer_axis()`, `row_blocks()`, `legend_ramp()` and `hover()` for hand-built
  figures. `legend_ramp()` draws a binned colour key with hairline outlines in the legend row, after the series items.
* Quantiles of whole people (`levels()`, `spread(discrete=True)`) use the inverted empirical CDF (R's type 1):
  the 0.9 quantile of daily peaks is the count that is enough on at least 9 of 10 days.
* `correlation()` shows its colour key as the binned `legend_ramp()` key in the legend row, with
  outlined squares, as the R package's `hl_correlation()` does now.
* The time-of-day window no longer gains an hour from float noise in a data limit: a span from 07:00 read
  6.999999999999998 once the axes were placed, and the axis started at 05:00 instead of 06:00.

### Surveys

* `likert()`: diverging bars for rating scales. The levels are binned so their colours can be told apart (a
  ten-point scale reads 1–2, 3–5 | 6–8, 9–10; `bins=` names others), a middle level is centred on the split,
  `reverse=` recodes and marks negatively worded items, `group=` draws sections, median, IQR and n stand beside
  each row, and the binned key sits in the legend row. Agreement takes the diverging ramp's first pole (blue).
* `spread(section=, panel_letters=, mean=, sort="median")`: rows in lettered blocks under their names, the mean as
  an open diamond beside the median, rows ordered by median; the legend row names median and mean.
* `bars(respondents=)`: multiple-choice answers as shares of the panel's respondents, each respondent once per
  answer, with a caption note that several answers were possible. `context=` draws categories in the context grey
  (an exclusive "none" answer), last when sorted by value; `header="n"` gives each facet its n instead of its
  total; `show_n="column"` writes each bar's n in a column right of the panel; `inside="name"` writes each stacked
  segment's name and value inside it, in greys by position, so rows may hold different answers.
* `HairlineFigure.numbers_column()` for a numbers column beside a hand-built panel; `legend_ramp(labels=)` names
  the steps of a binned key; the legend row takes a `"diamond"` (open marker) item.

### One design across charts

* Category and row names are set in ink in every chart, as spread, forest and Likert rows already were; numbers on
  the axes (years and lane numbers included) stay faint. Bar, ridgeline, raincloud and study panels change.
* Binned keys (`legend_ramp()`, the correlation heatmap, `likert()`, `lanes()`, `levels()`) start at the left
  edge after the series items, as every other legend does, instead of sitting at the right.
* Interval headings follow the locale: "Effect [95% CI]" in English, "Effekt [95 %-KI]" in German, on `forest()`,
  `dotplot()` and `study().effects()`.
* `levels(by=...)` shades its panels in greys unless `colors=` is given, as its binned key already was: the panel
  names say whose levels they are, and the hues stay free for the places drawn beside them.
* `colors="blues"` (any ramp name) on any chart gives ordered groups the steps of one ramp, light to dark.
* `dotplot(percent=True)` draws shares as percent; `arcs(key_title=)` names the width key, which now has a title
  by default.

### Options every chart shares

* One module (`charts/options.py`) applies the options every chart shares, so each works the same wherever it
  appears; `docs/guide/options.md` shows which chart has which.
* `reference=` (0.9, (0.9, "Target"), a list of them or {"Target": 0.9}) on `bars`, `spread`, `dotplot`,
  `raincloud`, `ridgeline`, `scatter`, `timeseries` and `kaplan_meier`: dashed lines on the value axis, labelled at
  their end, or above the rows on charts drawn as rows. `dotplot(reference=)` now draws this line instead of a
  plain null line.
* `highlight=` on the same charts keeps the named groups in colour and greys the others, legend included; on bars
  it now reaches bar series, and a highlighted group keeps the colour it has without the highlight.
* `key_title=` titles the legend row on every chart with a legend (`HairlineFigure.key_title()` on hand-built
  figures); `x_title=` and `y_title=` on every chart with axes (`x_title` is the same as `axis_title` on `spread`
  and `likert`).
* `min_n=` on `bars`, `scatter`, `likert` and `dotplot` (with `n=`); `sort=` ("median", "mean", "n") on `raincloud`
  and `ridgeline`; `percent=` on `raincloud`, `ridgeline` and `scatter`; `clip=` on `timeseries`;
  `show_n=False` on `raincloud`, `dotplot` (the n column then only counts for `min_n`) and `likert` (n left out of
  the key numbers); `dotplot(order=)`.
* `facet=` on `scatter`, `raincloud` and `ridgeline` (panels on shared axes, each with its own fit or comparisons;
  ridges on one height scale) and on
  `spread`, `dotplot` and `likert` (a block of rows per value under its name, on one axis; a group keeps its colour
  in every block).
* `ridgeline` keeps room above the top ridge for the labels of reference lines.
* Three gallery figures in both languages: `scatter_sites`, `spread_years` and `ridgeline_sites`; `dotplot_rates`
  draws a benchmark.

### Summaries: the same measures on every chart

* `summary=` chooses the marks on `raincloud`, `spread`, `ridgeline`, `dotplot` and `timeseries` from one
  vocabulary: `"median"`, `"mean"` (an open diamond), `"iqr"` (a thick bar), `"range"` (a thin line), and `"sd"`
  and `"ci"` (the mean's SD or 95 % CI as a slim bar). A summary you give is named in the legend; without one,
  each chart draws what it did before. See `docs/guide/summaries.md`.
* `stats=` writes the same measures as numbers: rows under the groups (raincloud), a column beside the ridges
  (ridgeline), the panel headers (timeseries, now also `"iqr"`, `"sd"`, `"ci"` and `"n"`) and the column of
  spread (now also `"sd"` and `"ci"`). Their labels follow the locale ("Spannweite", "95 %-KI").
* `dotplot(summary=("mean", "ci"))` takes one row per value and draws one row per label, with its n.
  `timeseries(summary=("median", "iqr"))` draws each x's centre as a line over its interval as a band.
* Legend keys `"tick"`, `"bar"` and `"slim"` for the marks; the numbers column beside a panel holds several
  measures per row, aligned.
* Numbers under the x axis never meet: `n = 20` shortens to `20` after the label `n`, and a row that still cannot
  stand apart stops the figure with what would fit.

### Comparisons

* `compare=` on `raincloud`, `spread`, `ridgeline` and `dotplot` (with `summary=`): each group's difference from one
  group or from the group before it (`"adjacent"`), with its 95 % CI and p, written beside the other numbers, never
  over the data. The test follows the centre: the Hodges–Lehmann shift and Wilcoxon rank-sum test with the median,
  the difference in means and Welch's t-test with the mean alone. The caption names it and, for several
  comparisons, says that p values are not adjusted.
* `numbers=` on `spread`, `dotplot` and `forest`: `"auto"` (beside the plot while it keeps its least width, else
  under each row, as before), `"right"` (always beside it) or `"below"` (always under each row).
* Messages that stop a figure name the chart that was called: a dot plot's says `dotplot`, not `forest`.

### Nothing overlaps

* `check_layout()` lists what a reader would see collide in a figure: text over text, text off the figure, marks
  outside their plot. Every gallery figure and the hard cases in `tokens/fixtures/stress.json` are checked on each
  test run, in both languages; `docs/guide/layout.md` has the rules.
* Marks stay inside their plot: data reaching an outer tick widens the axis by the largest mark's half-size.
* The plot grows until no two y labels meet; x axes take fewer ticks where their numbers would meet; names on an x
  axis wrap to their slot, and labels of several lines get their room under the axis.
* Values inside stacked bars show only where the segment holds them.
* Count axes tick at whole numbers; numbered categories (years) keep their order in `bars`; titles follow bars
  that turn horizontal.
* More groups than colours: `raincloud`, `spread`, `ridgeline` and `chord` draw them in one colour instead of
  refusing.
* `correlation` wraps long names and leaves values out of cells too small for them; `arcs` grows the figure for
  tall labels instead of refusing.

The R package mirrors all of this under the same names (`hl_bars(facet = ...)`, `hl_lanes()`, ...); a composed
figure there is `hl_rows()`.


## 0.2.1

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

### Fixes from the 0.2.0 stress test

* Study endpoints with more groups than the palette has colours (nine groups on an eight-slot palette), or a
  categorical variable with more categories than that, return their table, values and text with `figure=None` and
  a warning that says why, instead of failing. `describe()`, `compare()`, `distribution()`, `survival()` and
  `over_time()` follow the same rule.
* The log-rank test counts each group's number at risk and deaths at every event time from its sorted times at
  once, so it is linear in the rows: 100,000 rows take a fraction of a second. Its values are unchanged.
* Values too small to show within six decimals keep two significant digits: a median near 1e-9 reads
  0.0000000012 in tables, texts, spread key numbers, tooltips and axis labels, not 0.000000. Float noise is snapped
  away relative to the value, so values near 1e-11 keep their digits too.
* `save()` raises `HairlineLayoutError` itself when a figure cannot be laid out, as drawing does, instead of
  wrapping it in a `RuntimeError`. The R package now refuses the same figures in `hl_save()`.
* Brand files follow one rule for the shape of every section hairline reads: `color`, `color.palette`,
  `typography`, `defaults.hairline`, its `colors`, `groups`, `sizes` and `outputs`, and `meta` are mappings; a list
  (`typography.fonts`, `categorical`, a group's members) may be written as its single value
  (`categorical: harbor`); each font entry is a mapping. Anything else is an error naming the file, the key and
  what it holds. A key given twice in one mapping is an error naming its line, as in R, instead of the last one
  winning.
* `save()` refuses a dpi below 20, at which text is smaller than a pixel, instead of failing inside FreeType.
* A bar whose values are all missing draws no bar, no value label and no tooltip, instead of a bar labelled 0.
  For sorting and percent totals it counts as zero, as before.
* Study texts count one row in the singular: "1 participant", "1 row repeats an id", "1 value is infinite",
  "1 variable". `study(unit=...)` takes a plural noun, whose singular drops a final s, or a singular and plural
  pair such as `("mouse", "mice")`.
* `use(output=...)` refuses an unknown export type with `brand=False` too.
### Narrow figures (one column of a two-column page)

* Axes charts keep their plot room: when the title, legend, panel headers, axis or table would squeeze the panels
  below `spacing.min_plot_height` (8 x the base size, for all panel rows together, each row at least
  `min_panel_height`), the figure grows instead of failing with "figure too small". `scatter(by=...)` and
  `timeseries()` at 75 mm (`width_mm` from a host context) used to fail; the rule lives in the frame, so it holds
  for every axes figure, hand-built ones included. Figures with room to spare keep their size (the gallery is
  unchanged). It replaces the Kaplan–Meier-only `keep_plot_height()` and the `survival.min_plot` token. A chart
  can ask for more room (`HairlineFigure.min_plot`): `raincloud()` does, by its bracket levels, and the study
  overview asks for less (`study.overview_min_row` per group row), as its strip is sized from its rows.
* `HairlineFigure.resize(width_mm=None, height_mm=None)` sets a chart's size after the fact, as `hl_save(width_mm
  =, height_mm =)` does in R; a chart fitted to its content (forest, spread, ...) is fitted again for a new width.
  "Figure too small" (still raised for drawn panels) now names the height that fits: "make it at least 52 mm tall
  (figure.resize(height_mm=52))".
* `bars()` lies down when its category names, or the values over its bars, are too wide for upright bars at the
  figure's width (`bars.label_space` x the base size between neighbours), not only by label count and length:
  seven or eight department names collided at 85 mm, and eight already did at 120 mm.
* `raincloud()` comparison brackets keep room for their p labels: a short plot grows until every bracket level is
  taller than its label, instead of stacking the labels into the brackets above.
* `scatter()` draws points at the axis limits whole; limits end on a break, so the panel edge cut them in half.
* Numbers from 10^9 on are written in one short-scale unit per axis and per bar chart (`1.25 tn`, `0.8 tn`;
  German `Bio.`, `Mrd.`), with the tick step's decimals on axes and `numbers.compact_digits` on bars, instead of
  thirteen digits that ran past the bars and the figure. Tooltips keep the full number.

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
