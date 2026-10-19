# Changelog

## Unreleased

* `HairlineFigure.percent_axis()` takes `digits`, and the new `HairlineFigure.number_axis()` does the same for
  plain numbers: the decimals of the values a reader looks up in interactive output. A power of 89.6 % no longer
  shows as 90 % beside a 90 % target. Without `digits` tooltips follow the shared digits rule as before; ticks
  are unchanged.
* `import hairline` no longer loads pandas. Chart and study functions load on first use, so a figure drawn with
  `figure()` and saved as SVG or HTML never imports pandas, and `import hairline` takes about 40 % less time.

## 0.1.0

* First release.
