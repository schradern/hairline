# Backlog: requests from use

What a real report needed beyond the current API, with the workaround it took and a proposal. Source: a German
quality report on a perioperative drug (2026-11), aggregated data, 4 procedure groups of very different size
(272 to 10,000 cases), children and adults, five years with two incomplete ones, typeset in a document tool that
does not render Markdown tables.

Every proposal is meant for both packages under the same name (`bars(...)` / `hl_bars(...)`) and for
`tools/parity.py`. Most are optional arguments on existing charts, so existing calls keep their output.

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
