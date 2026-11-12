# Backlog: requests from use

What a real report needed beyond the current API, with the workaround it took and a proposal. Source: a German
quality report on a perioperative drug (2026-11), aggregated data, 4 procedure groups of very different size
(272 to 10,000 cases), children and adults, five years with two incomplete ones, typeset in a document tool that
does not render Markdown tables.

Every proposal is meant for both packages under the same name (`bars(...)` / `hl_bars(...)`) and for
`tools/parity.py`. Most are optional arguments on existing charts, so existing calls keep their output.

## Status (2026-11)

**Every item below is in both packages** (see `python/CHANGELOG.md`, "Unreleased", and `r/NEWS.md`, "development
version"), under the same names (`bars(facet=...)` / `hl_bars(facet = ...)`), with tests and five new gallery
figures in both languages (`bars_facets`, `spread_doses`, `table_characteristics`, `unit_day`, `swimlanes_day`),
all in `tools/parity.py`: every gallery figure agrees within 1 pt, frame positions and tooltips. The correlation
heatmap now adds the binned key of item 18 itself, in both languages.

**Third report (items 20 to 25): in both packages**, with four gallery figures in both languages
(`likert_visits`, `spread_importance`, `bars_sources`, `bars_answers`), all in `tools/parity.py`. Where the shipped
form differs from the proposal:

* Item 20: `likert(..., group=)` as proposed. Agreement takes the diverging ramp's first pole (blue on the default
  ramp) and disagreement the other, as readers of rating charts expect; `ramp=` picks another diverging ramp. The
  binned key names its bins (`legend_ramp(labels=)`).
* Item 21: on `spread` the section column is `section=`, since `group` already names the rows.
* Item 23: `show_n="column"` needs horizontal bars (they lie down when it is given).
* Item 24: `inside="name"` draws one panel (no `facet`); its segments are tooltip targets of their own.
* Item 25: `respondents=` takes one answer per row and no `value`, `by` or `percent`; the axis of a share of
  respondents ends at 100 %.

Where the shipped form differs from the proposal:

* Item 1: `facet` is on `bars`; the location figure is `bars(facet=..., top=6)`. Since then `facet` is shared by
  every chart with groups (see `docs/guide/options.md`): panels on scatter, raincloud and ridgeline, blocks of rows
  on spread, dot plot and Likert.
* Item 3: `dotplot` takes the n from a column (`n="patients"`), as its rows are already aggregated; `raincloud`
  already writes n under each group.
* Item 5: `clip` applies to the value axis (y on `scatter`).
* Item 9: integer quantiles are opt-in (`spread(discrete=True)`, always in `levels()`), so existing calls keep
  their medians. They use R's type 1 (numpy `inverted_cdf`), not numpy's `higher`: the smallest count reached on
  at least that share of days, which is the "enough on 9 of 10 days" the decision line means. The median-gap
  warning needs at least 10 values.
* Item 15: composition is `figure(panels=..., heights=..., sharex=True)` with `lanes/levels/swimlanes(...,
  into=figure, panel=i)`; rows sized with `heights` share y only when asked.
* Item 16: `time_axis()` is a method on any figure; `timeseries` keeps its date axis.
* In R, item 15's composition is `hl_rows(hl_lanes(...), hl_levels(...), heights = c(9, 3, 4))`: R has no
  `figure()` to draw into, so finished plots are stacked as the rows of one frame, one time axis shared and
  labelled at the bottom. Item 18 is `hl_legend_ramp()`, added to any ggplot with `+`; item 11 is `hl_report()`
  with `hl_report_add()` and `hl_report_write()`.
* `table_characteristics` is drawn at the double size in both languages: at one and a half its "Early
  mobilisation" heading needed to wrap by 0.06 pt in Python, closer than the two languages' text measurement
  agrees, so the gallery figure now has room for its headings in one line.

## 1. Facets with their own scale

**Seen:** counts per year for four groups, one about 30 times larger than the smallest. Stacked bars flattened the
small groups to a line; grouped bars on one axis did the same.

**Today:** `figure(panels=4, layout="compose", columns=2)`, then matplotlib `ax.bar`/`ax.barh` by hand, value labels,
`ylim` per panel, `categories()` and `panel_header()` per panel, colours from `entities.colors_for`. About 40 lines,
outside hairline's layout checks.

**Proposal:** `bars(data, category, value, facet="group", scales="free" | "shared", columns=2)`: one panel per facet
value, each with its own value axis (`free`) or one shared axis, value labels as in `bars`, the panel header with the
facet name and its total. The same `facet` on `spread` and `dotplot` would cover the location figure (top n
categories per group, the rest as "other": see `top=` below).

* `top=6, other="übrige"` on `bars`: keep the n largest categories per panel, fold the rest into one bar.
* Panel totals in the header (`gesamt 281`), as the timeseries panels show key numbers.

## 2. Incomplete periods

**Seen:** the first and last year covered 2 and 10 months.

**Today:** alpha set per bar, the caption written by hand.

**Proposal:** `partial={"2021": "2 Monate", "2026": "10 Monate"}` on `bars` (and `timeseries`): those categories are
drawn lighter, and the caption gets one sentence naming them ("unvollständig, heller: 2021 (2 Monate), 2026
(10 Monate)"), in the locale.

## 3. n per group

**Seen:** every row of three figures needed its n.

**Today:** the n string-joined into the group label (`"RA ohne Beatmung (n = 272)"`), which also changes the label
that colours and `order` key on.

**Proposal:** `show_n=True` on `spread`, `bars`, `dotplot`, `ridgeline`: the n in the numbers column (spread) or
after the category label, formatted in the locale; colours and `order` keep keying on the bare group.

## 4. Minimum n

**Seen:** one reference was documented in a single case; a distribution of one value says nothing.

**Today:** a filter before the chart and a caption note listing what was dropped.

**Proposal:** `min_n=10` on `spread`, `ridgeline`, `raincloud`: groups below it are not drawn, and the caption names
them ("nicht dargestellt (unter 10): Lokalanästhetikum"). Combined with `show_n`.

## 5. Clipping outliers

**Seen:** a few implausible doses (thousands of mg) squashed the axis of a spread chart.

**Today:** cap at the 99th percentile by hand; the count and the limit written into the caption.

**Proposal:** `clip=0.99` (a quantile) or `clip=(low, high)` (values) on `spread`, `raincloud`, `ridgeline`,
`scatter`: values outside are not drawn, the statistics still use every value (or `clip_stats=True` to exclude them),
and the caption says how many are hidden and where the limit lies, in the locale.

## 6. Colour by a coarser grouping

**Seen:** 12 rows (procedure × age group) on an 8-slot palette.

**Today:** `colors={label: color_of(procedure) for label in labels}`, built by hand.

**Proposal:** `color_by="procedure"` on every chart with groups: rows are drawn per `group`, coloured by the coarser
column, the legend lists the coarser values. The palette check then counts the coarser values.

## 7. Colour scopes across figures

**Seen:** the session had given slots 1–4 to the four procedures; a later figure of application patterns
(single bolus / repeated / infusion) took slots 1–3 again, so "single bolus" was the blue of one procedure.

**Today:** `colors=dict(zip(patterns, palette(n=7)[4:]))` by hand.

**Proposal:** `dimension="pattern"` on a chart (or a `scope()` context): categories of a different dimension avoid
the slots the session has fixed for another dimension, as long as the palette has room; an error naming both
dimensions when it does not.

## 8. Shares from counts

**Seen:** a 100 % stacked bar of pattern shares per group.

**Today:** shares computed before `bars(percent=True)`, the n per group lost.

**Proposal:** `normalize=True` on `bars` with counts: hairline computes the shares per category, labels them, and
keeps the n for `show_n`.

## 9. Discrete values and the median

**Seen:** doses documented on round levels (25 and 50 mg); the median, 35, lay between the two and matched neither.
The report had to say so in a footnote.

**Proposal:** `spread` (and `describe()`) warn when the median falls in a gap between two levels that each hold a
large share (for instance > 20 % of the values each), or offer `stats=("levels",)`: the two or three most frequent
values with their shares, in the numbers column.

**Also seen** (second report, below): counts of people per time of day. A mean of 1.4 doctors means nothing, and an
interpolated quantile of counts can be fractional too. Whatever hairline computes from integer data (median,
quantiles, the decision line in item 14) should stay on the data's levels (`method="higher"` in numpy, `type = 1`
in R) when the column is integer, and say so in the caption.

## 10. Tables for documents

**Seen:** the report's three tables (counts per year, characteristics per group, timing) were lost when typeset:
the document tool dropped Markdown tables. They went over as pandas code.

**Today:** `study(...).describe()` returns a table of formatted strings (it could have built the characteristics
table), but nothing renders a table, and aggregated frames (counts per year) do not fit `study`.

**Proposal:** `table(data, title=None, caption=None, footnotes=None, bold_rows=None, align=None, size=...)` for any
frame of strings or numbers (numbers formatted in the locale), rendered in hairline's typography and exported by
`save()` as PDF, PNG, SVG and HTML. `Result.table` from `describe()`/`compare()` passes straight in.

## 11. Report numbering (optional, larger)

**Seen:** the document tool numbered tables as figures ("Figure 3" for the first figure) and in English.

**Proposal:** a small `report()` that collects figures and tables in order, numbers them in the locale
("Abbildung 1", "Tabelle 2"), and writes self-contained Markdown or HTML with captions and the images embedded. Only
if it stays small; the rest of the document belongs to the document tool.

# Second report: occupancy and staffing over the day

Source: anaesthesia staffing for one surgical unit (2026-11): bed occupancy minute by minute in 9 places of four
sections (2 induction rooms, 2 theatres, 1 emergence room, 4 recovery places) over half a year, the moves between
them, and from these the doctors and nurses needed at the same time. The question was how many whole people each
time of day needs, without averages hiding the extremes and without a rare short peak adding a person. Built in
matplotlib by hand; the figures only imitated hairline (fonts, sizes, frame, legend and export were set by hand), so
they drifted from it in every round of review. Items 12 to 19 are what that took.

## 12. Lanes over the time of day

**Seen:** the core figure: one row per place, the time of day across, the colour of each 15-minute cell = the share
of days the place was occupied then. Readers took it in at once; averages per section hid that two patients are in
theatre while a third waits in induction.

**Today:** `pcolormesh` per row with a one-hue colormap from `colormap()`, row labels set by hand, section separators
drawn as `axhline`, about 60 lines with item 13.

**Proposal:** `lanes(data, row, start, end, *, group=None, bin=15, value="share" | "count", days=None, colors=None)` /
`hl_lanes(...)`: intervals per row (or a precomputed share matrix), binned over the time of day, coloured from the
row's or its `group`'s ramp, with the binned key of item 18 in the legend row. `group` draws the rows as blocks:
the group name once, in its colour, the rows as plain numbers (1, 2, …), a hairline between blocks. `days=` the
calendar filter (weekdays, weekends, a list), named with its n in the subtitle. The x axis is the time of day,
cropped to the hours with data (item 16).

## 13. Moves between lanes

**Seen:** where patients go next and when: induction → theatre → emergence → recovery, and a few that start in
recovery (a holding stay) before induction.

**Today:** a vertical segment per (from, to, 15-minute bin) between the two rows, the alpha from the moves per day,
drawn behind the lanes so it shows only in the gaps; a frequency floor so rare moves are not drawn.

**Proposal:** `flows=` on `lanes`: a frame of (from, to, time) events; one connector per pair and bin, strength from
the events per day (reference and floor as arguments), coloured by the destination's row. A legend item "move".
`sankey` stays for flows across categorical columns; this is the time-of-day case it cannot draw.

## 14. Counts of people as steps

**Seen:** below the lanes, doctors and nurses needed at the same time over the day. Three things in one panel: how
often exactly 1, 2, 3 … were needed (one shaded row per count, as in item 12), the typical day (median, dashed) and
the staffing that is enough on 9 of 10 days (a bold step). People only come whole, so every line is a step on
integer levels.

**Today:** per-day peaks per bin, `np.quantile(..., method="higher")`, two `step(where="post")` calls and the shaded
rows by hand. `timeseries` draws raw values under a rolling mean, which is wrong for whole units.

**Proposal:** `levels(data, time, count, *, by=None, bin=15, quantile=0.9, typical="median", shade=True)` /
`hl_levels(...)`, or `timeseries(kind="step", quantiles=(0.5, 0.9))`: integer y axis, the distribution as shaded
count rows, the decision line bold and the typical line dashed, both on the data's levels (item 9). Panel header
with the key numbers ("bis 3 · typisch 2").

## 15. Shared time axis, unequal heights

**Seen:** one figure, three panels on the same time axis: 9 place lanes above, two short count panels below, so the
cause (patients) sits right above the effect (staff).

**Today:** `add_gridspec(height_ratios=...)` and `sharex` by hand, outside hairline's frame; panel titles and the
legend row placed by eye.

**Proposal:** `figure(panels=3, layout="rows", heights=(9, 3, 4), sharex=True)` (and the same on the R panel
composition): rows sized by content, one x axis labelled once at the bottom, the frame's legend row and panel
headers as usual.

## 16. Time-of-day axis

**Seen:** every figure ran over 00–24 with long empty nights, or had to be cropped by hand.

**Proposal:** a time-of-day scale for `lanes`, `levels`, `timeseries` and item 17: hour labels ("06", "08" …) in the
locale's form, cropped to the first and last hour with data plus a margin (`crop=True`, or `hours=(6, 22)`), an
optional shaded span for a named period (`spans={"Regelzeit": (7, 16)}`) with its label in the legend row.

## 17. Swimlanes for one day

**Seen:** what the averages could not show: one real day, which patient is where, and which person covers them.
Rows for the places (bars per patient, P1, P2 …, with the narcosis as a darker inner line), then rows per doctor and
per nurse with their tasks, each task given to the first free person.

**Today:** rectangles per segment and text by hand, about 90 lines; the row blocks (places, doctors, nurses) labelled
by hand.

**Proposal:** `swimlanes(data, row, start, end, *, label=None, color_by=None, inner=None, group=None)` /
`hl_swimlanes(...)`: one bar per interval in its row, coloured by `color_by`, the label inside when it fits, an
optional inner interval drawn as a darker line (`inner=("inner_start", "inner_end")`), row blocks as in item 12, the
time-of-day axis of item 16. An optional `assign="first_free"` that turns a list of tasks into rows of people would
cover the staffing case, but could also stay with the caller.

## 18. A binned colour key

**Seen:** the key for "share of days". A gradient bar looked wrong in the frame; four small outlined squares
(25 %, 50 %, 75 %, 100 %) in the legend row, next to the line samples, read well.

**Today:** a second `fig.legend` with `Patch` handles and a hairline edge, placed by eye on the right of the legend
row. The legend row's `square` kind has no outline, and the row takes one list of items.

**Proposal:** `legend_ramp(ramp, steps=(0.25, 0.5, 0.75, 1), title="Anteil der Tage", format="percent")` (R:
`hl_legend_ramp()`), drawn right-aligned in the same legend row as the series items, squares with the hairline
outline so the lightest step stays visible on the surface. Charts with a ramp (`lanes`, `levels`, `correlation`)
add it themselves.

## 19. Decision tables from counts over time

**Seen:** the answer in numbers: per role and time block (regular hours 07–16, service 16–07), the staffing that
covers 9 of 10 days, and for each staffing level what it leaves uncovered (person-minutes, longest overload, share
of days fully covered, utilisation). A bar chart of the uncovered minutes per level, with the chosen level marked,
was tried and dropped: with a tolerance of 0 the chosen bar has height 0.

**Today:** pandas only; nothing in hairline.

**Proposal:** none for now beyond item 10's `table()`: the tradeoff table with the chosen row in bold
(`bold_rows=`) is the readable form. Worth noting as a case where a chart was the wrong form.

## Rules this report confirmed

* **Whole units stay whole.** Counts of people or places are drawn as steps and shaded levels; means appear only as
  context (item 9).
* **One channel per meaning.** Position = place and time of day, colour = how often, lines = events (moves) and
  decisions (staffing).
* **Cause above effect** on one shared time axis (item 15).
* **Show the distribution and the decision line together.** A percentile of daily peaks alone hides the extremes
  or overstates them.
* **Quiet text, hairline weights.** Panel titles regular weight in the secondary ink, explanations in the subtitle;
  about 0.5 pt for events and separators, 0.9 pt for the decision line, 0.4 pt for outlines. Every round of review
  that changed these by hand drifted from hairline's tokens; the fix is to build on `use()` / `figure()` / `save()`
  and add the missing charts here, not to imitate the style.

## Already there, used too little

* `format_number(value, digits)` and `format_percent(share)` format in the locale (decimal comma, true minus sign).
  Captions written as f-strings showed "129.86" in a German figure until fixed by hand.
* `study(data, group=..., variables=...).describe()` builds a characteristics table per group with n, median (IQR)
  and shares as formatted strings, plus a sentence of text.
* `colormap(name)` and `ramp(name, n)` give one-hue ramps for `pcolormesh` and `imshow`; the lanes of item 12 can use
  them today, only the chart and its key are missing.
* The legend row takes `square` items (`HairlineFigure.legend([("square", color, label), …])`); a binned key can be
  built from them by hand until item 18, apart from the outline.

# Third report: a questionnaire survey

Source: four figures of a questionnaire survey (2026-11), drawn without hairline: statements rated on a 10-point
scale in sections, importance ratings of many items in lettered panels, multiple-choice questions with an exclusive
"none" answer, and single-choice questions as stacked bars. Not everyone answered every question, so the n differs on
almost every row. Items 20 to 25 are what each figure would need from hairline, and where the figure itself is the
wrong form. The gallery shows them on synthetic data of another topic.

## 20. Diverging bars for rating scales

**Seen:** statements rated 1 to 10, one row each in sections, the share of each rating stacked to the left
(1–5) and right (6–10) of a centre line, ten shades from red to blue, a key under the axis and a numbers column with
median [IQR] and n. The split shows the balance per statement at a glance; the ten shades do not: no reader maps a
shade back to its rating, the palest steps (5 and 6) meet at the centre and read as a gap, and the key sits far from
the bars. Some statements are worded negatively, marked only in their label, so on those rows red is the good
answer.

**Today:** nothing in hairline; `bars(percent=True, stacked=True)` stacks from zero, not from a split.

**Proposal:** `likert(data, item, rating, *, levels=range(1, 11), split=5.5, bins=None, group=None, reverse=None,
stats=("median", "iqr", "n"))` / `hl_likert(...)`: per item the share of each level, stacked away from the split (a
middle level, when the scale has one, centred on it), on a percent axis that reads outward from 0. `bins` collapses
levels into a few labelled steps (`{"1–2": (1, 2), "3–5": (3, 5), "6–8": (6, 8), "9–10": (9, 10)}`), so the colours
can be told apart; the default for more than six levels is two or three bins per side. `group` draws the items as
blocks with their name once, as item 12's rows; `reverse` names the negatively worded items, recoded and marked
("reversed") so colour keeps one meaning; `stats` is spread's numbers column (median [IQR] and n per row, on the
data's levels as item 9). The key is item 18's binned key on a diverging ramp, in the legend row. Rows keep their
given order within a block, or `sort="balance"`.

## 21. Mean beside median, items in sections

**Seen:** importance ratings of many items in lettered panels (a, b, c), each row with its IQR as a grey bar, the
median as a dot, the mean as an open diamond and its n in the label, rows sorted by median.

**Today:** `spread(stats=("median", "iqr", "n"), show_n=True)` draws one panel of these rows with the numbers beside
them; the mean is a number, not a mark, and there are no sections or panel letters. On a 10-point scale the median
and IQR are whole or half steps, which `discrete=True` keeps on the levels.

**Proposal:** `spread(..., mean=True)` draws the mean as an open marker on the row (the legend row then names median,
mean and IQR), `group=` draws blocks of rows with their name as a panel header, `panel_letters=True` letters them
as `figure()` does, and `sort="median"` orders rows within a block. The rows of one block keep one axis; blocks
share it.

## 22. One category drawn as context

**Seen:** two multiple-choice questions as horizontal bars of the share of respondents, the exclusive "none" answer
as a grey bar among the blue ones. Two panels side by side, each with its own n written into its axis title.

**Today:** `bars(...)` with `horizontal=True`; one category in grey needs `colors=` per group, which a single series
does not have, and the n per panel goes into the axis title by hand. Two panels from different questions are two
calls and a composition.

**Proposal:** `context=` on `bars` names categories drawn in the context grey, kept in their sorted place (or last
with `sort="value"`, as an answer outside the ranking). With `facet=`, `header="n"` writes each panel's n in its
header ("n = 160") instead of the total, so shares from questions of different n sit side by side.

## 23. An n column on stacked bars

**Seen:** 100 % stacked bars of single-choice questions, one row per question, n written right of each bar, as the
rating figures write theirs.

**Today:** `bars(percent=True, stacked=True)` with values inside the segments; `show_n` puts the n after the label,
not in a column.

**Proposal:** `show_n="column"` on `bars` (and on item 20): the n right-aligned in a column beside the bars, in the
key-number style of spread's numbers column, so rows with different n read alike in every chart.

## 24. Rows with their own answers

**Seen:** a panel of questions whose answers differ per row (yes/no/unsure on one row, two named options on the
next), each segment named and valued inside in greys, without a legend.

**Today:** stacked bars need one set of groups for every row; their names go to the legend row, and inside a
segment only the value is written.

**Proposal:** `inside="name"` on stacked bars: the segment's name and value inside it, where it fits (as item 17's
labels), and no legend entry for names written inside. Rows may then hold different groups; their colours come from
a neutral ramp by position (first answer darkest), since colour would otherwise suggest that the first answers of
two different questions are the same thing. Questions with different answers are usually better as separate rows of
item 23 or as a table (item 10); worth keeping the option small.

## 25. Shares of respondents for multiple choice

**Seen:** a multiple-choice question: several answers per respondent, so the shares add up to more than 100 %, and
the exclusive answer excludes the others.

**Today:** shares computed before `bars`, the n written into the axis title.

**Proposal:** `bars(data, category, respondents="id")` counts each respondent once per answer and divides by the
number of respondents (not answers), the axis says so ("% of respondents, n = 160"), and the caption notes that
several answers were possible, in the locale. Combined with item 22's `context=` for the exclusive answer.

## Rules this report confirmed

* **A key no one can read is no key.** Ten shades on one scale are decoration; bin to what a reader can tell apart
  (two or three steps per side) and name the bins.
* **Colour keeps one meaning.** Negatively worded items are recoded or marked, so red never means agreement in one
  row and disagreement in the next.
* **The n belongs to every row** when the rows come from questions that not everyone answered: one column, in the
  same place in every chart (items 20 and 23).
* **Mean and median together only on a coarse scale.** On a 10-point rating they differ enough to tell skew; on
  continuous data the median and IQR alone are the cleaner form (spread).

## Already there, used too little

* `spread(stats=("median", "iqr", "n"), show_n=True, discrete=True)` draws item 21's rows today, with the numbers
  column the rating figure also wants.
* `bars(facet=..., scales="shared")` draws item 22's two panels from one long frame, each panel with its own
  categories.
* `legend_ramp()` / `hl_legend_ramp()` takes a diverging ramp and any steps, so a binned key for item 20 can be
  added by hand until the chart exists.
