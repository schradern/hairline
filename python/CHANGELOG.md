# Changelog

## Unreleased

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

## 0.1.0

* First release.
