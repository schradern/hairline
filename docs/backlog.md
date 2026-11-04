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

## Already there, used too little

* `format_number(value, digits)` and `format_percent(share)` format in the locale (decimal comma, true minus sign).
  Captions written as f-strings showed "129.86" in a German figure until fixed by hand.
* `study(data, group=..., variables=...).describe()` builds a characteristics table per group with n, median (IQR)
  and shares as formatted strings, plus a sentence of text.
