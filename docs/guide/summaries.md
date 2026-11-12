# Summaries: the same measures on every chart

Distribution charts draw and write their measures under one vocabulary, the same in Python and in R. `summary`
chooses the marks, and `stats` writes the same measures as numbers.

| Name | Measure | Mark |
|---|---|---|
| `median` | Median | A tick across the box (raincloud), a line up to the ridge (ridgeline), a dot (spread, dot plot) |
| `mean` | Mean | An open diamond |
| `iqr` | Interquartile range | A thick bar: the box, the band |
| `range` | Smallest to largest value | A thin line |
| `sd` | Mean ± 1 standard deviation | A slim bar |
| `ci` | 95 % confidence interval of the mean (t distribution) | A slim bar |
| `n` | Number of values | Numbers only |

The IQR, SD and CI bars sit in the same place, so a chart draws one of them; naming two is refused. A summary you
give is named in the legend. Without one, each chart keeps its familiar marks.

| Chart | `summary` | `stats` writes the numbers |
|---|---|---|
| `raincloud` | Any; default `("median", "iqr")` | In rows under the groups |
| `spread` | Any; default `("median", "iqr", "range")` | In the column beside the rows (also `"levels"`) |
| `ridgeline` | `median`, `mean` (a ridge shows its own spread) | In a column beside the ridges |
| `dotplot` | One centre and its interval: the rows are values, one row per label | In the column of estimates |
| `timeseries` | One centre and its interval, per x: a line over a band | In the panel headers (also `"share_above"`) |

A centre drawn with its interval keeps the pair that belongs together: the IQR with the median, the SD and CI with
the mean, and the range with either.

```python
hl.raincloud(stays, "unit", "days", summary=("median", "mean", "iqr", "range"),
             stats=("median", "iqr", "mean", "ci"))
hl.dotplot(stays, "unit", "days", summary=("mean", "ci"))
hl.timeseries(scores, "day", "score", "ward", summary=("median", "iqr"), stats=("median", "iqr", "n"))
```

```r
hl_raincloud(stays, "unit", "days", summary = c("median", "mean", "iqr", "range"),
             stats = c("median", "iqr", "mean", "ci"))
hl_dotplot(stays, "unit", "days", summary = c("mean", "ci"))
hl_timeseries(scores, "day", "score", "ward", summary = c("median", "iqr"), stats = c("median", "iqr", "n"))
```

Numbers follow the [layout rules](layout.md). Numbers under the groups that would meet first shorten
(`n = 20` becomes `20` after the label `n`). If they still cannot stand apart, the figure stops and names what
would fit: fewer stats or groups, a wider size, or `spread()`, which lists the numbers in a column.

## Comparisons

`compare` writes each group's difference from one group (`compare="Unit A"`) or from the group before it
(`"adjacent"`), with its 95 % CI and p, next to the other numbers, never over the data. Raincloud writes them in rows
under the groups. Spread and ridgeline write them in the column beside the rows, comparing within each block or
panel. The dot plot, with `summary`, writes them in two columns.

The test follows the chart's centre, and the caption names it:

| Centre | Δ | p |
|---|---|---|
| Median (the default) | Hodges–Lehmann shift, distribution-free 95 % CI | Wilcoxon rank-sum test |
| Mean alone (`summary=("mean", ...)`) | Difference in means, Welch's 95 % CI | Welch's t-test |

With more than one comparison, the caption adds that p values are not adjusted for multiple comparisons.
`compare="all"` is refused because no row can hold a number for every pair. Raincloud's `comparisons=` brackets show
all pairs.

```python
hl.spread(stays, "unit", "days", stats=("median", "n"), compare="Surgical")
hl.dotplot(stays, "unit", "days", summary=("mean", "ci"), compare="adjacent")
```

## Where the numbers go

Spread, the dot plot and the forest plot write their numbers beside the plot while it keeps its least width, and
under each row on a narrower figure (`numbers="auto"`). `numbers="right"` keeps them beside the plot, which may then
be narrower. If the plot would be narrower than `spacing.min_plot_beside`, the figure stops and says so.
`numbers="below"` always writes them under each row.
