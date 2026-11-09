# Options every chart shares

Some questions come up in every chart: which groups to show and in what order, what to compare against, what to
point at, how to split the data into panels. hairline answers each of them with one option, under one name, that
works the same way in every chart that has the concept, in Python and in R. Each option is built once in each
package (`charts/options.py`, `chart_options.R`), so a chart that offers it cannot drift from the others.

| Option | `bars` | `spread` | `dotplot` | `raincloud` | `ridgeline` | `scatter` | `timeseries` | `kaplan_meier` | `likert` | `lanes` | `levels` | `arcs` |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `order` | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| `sort` | ● | ● | ● | ● | ● |  |  |  | ● |  |  |  |
| `colors` | ● | ● |  | ● | ● | ● | ● | ● |  | ● | ● |  |
| `highlight` | ● | ● | ● | ● | ● | ● | ● | ● |  |  |  |  |
| `key_title` | ● | ● |  | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| `x_title` | ● | ● | ● | ● | ● | ● | ● | ● | ● |  |  |  |
| `y_title` | ● |  |  | ● |  | ● | ● |  |  |  |  |  |
| `reference` | ● | ● | ● | ● | ● | ● | ● | ● |  |  |  |  |
| `percent` | ● | ● | ● | ● | ● | ● | ● |  |  |  |  |  |
| `show_n` | ● | ● | ● | ● | ● |  |  |  | ● |  |  |  |
| `min_n` | ● | ● | ● | ● | ● | ● |  |  | ● |  |  |  |
| `clip` |  | ● |  | ● | ● | ● | ● |  |  |  |  |  |
| `facet` | ● | ● | ● | ● | ● | ● |  |  | ● |  |  |  |

An empty cell is a chart without the concept: a Likert row has no single value to draw a reference at, a dot plot
has one series and so no legend, and the dot plot takes its n from a column (`n=`) instead of counting rows.

## What each option does

| Option | Meaning |
|---|---|
| `order` | The groups in this order; groups left out are not drawn. |
| `sort` | Groups by a statistic, highest first: `"median"`, `"mean"` or `"n"` on distributions, `"value"` on bars, `"balance"` (agreement less disagreement) on Likert. Ties keep the given order. |
| `colors` | Colours for this chart only, `{"Unit B": "#e79d01"}`, or a ramp name, `"oranges"`, for ordered groups (light to dark in the chart's order). |
| `highlight` | Groups kept in their colour; every other group is drawn in the context grey, its legend swatch too. A group keeps the colour it has without the highlight. |
| `key_title` | A title at the start of the legend row, naming what the groups are. |
| `x_title`, `y_title` | Axis titles: under the plot on the right, above the plot on the left. |
| `reference` | Dashed lines on the value axis: a value, several, or labelled ones, `{"Target": 0.9}` (`c(Target = 0.9)` in R). Labels sit at the line's end, or above the rows on charts drawn as rows. |
| `percent` | Shares (0 to 1) drawn and labelled as percent. |
| `show_n` | Each group's n: after its name, under it on raincloud, among the key numbers on Likert, in the panel header with `facet`. Where it is on by default (raincloud, Likert, the dot plot's `n=` column), `show_n=False` leaves it out. |
| `min_n` | Groups with fewer values (rows) are left out; the caption names them. |
| `clip` | Implausible values hidden: `0.99` hides those above the 99th percentile, `(low, high)` those outside; the caption says how many, and the statistics use every value unless `clip_stats`. |
| `facet` | One panel per value of a column. Charts with axes (bars, scatter, raincloud, ridgeline) draw panels side by side on shared axes, each with its own key numbers; charts drawn as rows (spread, dot plot, Likert) draw a block of rows per value under its name, on one axis. A group keeps its colour in every panel. |

## Examples

```python
hl.scatter(patients, "SOFA score", "Lactate (mmol/l)", by="group", facet="site",
           order=["Low risk", "Medium risk", "High risk"], colors="oranges", key_title="Risk",
           reference={"Upper normal": 2})
hl.spread(occupancy, "ward", "occupied", facet="year", highlight=["Unit B"], reference={"Planned": 10},
          x_title="Occupied beds at 00:00")
hl.dotplot(rates, "unit", "mortality", "low", "high", percent=True, reference={"Benchmark": 10},
           highlight="Burns", min_n=30, n="patients")
```

```r
hl_scatter(patients, "SOFA score", "Lactate (mmol/l)", by = "group", facet = "site",
           order = c("Low risk", "Medium risk", "High risk"), colors = "oranges", key_title = "Risk",
           reference = c(`Upper normal` = 2))
hl_spread(occupancy, "ward", "occupied", facet = "year", highlight = "Unit B", reference = c(Planned = 10),
          x_title = "Occupied beds at 00:00")
hl_dotplot(rates, "unit", "mortality", "low", "high", percent = TRUE, reference = c(Benchmark = 10),
           highlight = "Burns", min_n = 30, n = "patients")
```

In R, `?chart_option_params` documents the shared options once; every chart's help page inherits them.
