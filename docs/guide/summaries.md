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
