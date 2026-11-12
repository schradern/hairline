# Nothing overlaps

Every hairline chart, in Python and in R, follows the same layout rules, so a figure reads cleanly at every size
without being tuned by hand. When something cannot fit, the chart makes room in a predictable way. Only when no
room can be made does it stop, with a message that says what would fit.

| What | Rule |
|---|---|
| Points and other marks | Stay inside their plot. Data that reaches an outer tick widens the axis by the largest mark's half-size (a point's radius, half a censor tick), so no mark is cut by the edge. |
| Names on the y axis | Never meet. The plot grows until neighbouring labels keep a gap, and only as far as they need. |
| Numbers on the x axis | Stand apart. Where they would meet, the axis takes fewer ticks. |
| Names on the x axis | Wrap to their slot. A single word wider than its slot stops the figure, with the room it needs and what to use instead (a wider size, fewer groups, or a chart that lists groups as rows). |
| Labels below the x axis | Take the lines they need, so a two-line label never runs into the axis title. |
| Values inside bars | Show only where the segment holds them, along and across. The total at the bar's end stays. |
| Counts | Tick at whole numbers. Numbered categories, such as years, keep their own order. |
| Turned bars | Bars that turn horizontal because their names are long take their axis titles with them. |
| More groups than colours | Groups named on an axis or around a circle (raincloud, spread, ridgeline, chord) share one colour, since their names identify them. Charts that tell groups apart only by colour still refuse, with a suggestion. |
| Drawn charts | Labels wrap into the room the chart leaves. A heatmap whose cells cannot hold their values shows colour only, read with the key. Arcs keep room for their arcs, and the figure grows to hold tall labels. |

## Checking a figure

`check_layout()` in Python and `hl_check_layout()` in R list anything a reader would see collide: text over text,
text off the figure, or marks outside their plot. An empty list means none.

```python
figure = hl.bars(counts, "unit", "patients")
hl.check_layout(figure)  # []
```

```r
plot <- hl_bars(counts, "unit", "patients")
hl_check_layout(plot, size = "single")  # list()
```

Both packages check every gallery figure and a set of hard cases on each test run: many groups, long names,
outliers at the edge and the smallest size. The hard cases live in `tokens/fixtures/stress.json`, so both languages
draw the same figures.
