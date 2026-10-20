# hairline

Clean, predictable figures for medical and data science. One frame for titles, legends, panels and captions,
one type scale, colour-vision checked palettes, and print-ready files. The R package of the same name draws
the same figures from the same design tokens, so a Python figure and an R figure in one manuscript match.

```bash
pip install "hairline @ git+https://github.com/schradern/hairline#subdirectory=python"
```

That installs the development version this page describes. The 0.1.0 release on PyPI (`pip install hairline`)
lacks the unrounded `.numbers` of study results and the later fixes in the [changelog](CHANGELOG.md).

Python 3.11 or later, matplotlib 3.11 or later: from 3.11 matplotlib kerns text as R does, so both packages
place every label alike. The bundled font, Hairline Sans, needs no installation.

![ICU bed occupancy in small multiples, drawn with hairline](https://raw.githubusercontent.com/schradern/hairline/main/docs/images/hero.png)

## From data to a result

Most studies need the same few results: a cohort description, a comparison between groups, effects, events
over time. `study()` takes a data frame once, with the role of each column, checks the data, and returns each
result as a figure, a table, the key values and a sentence for the text.

```python
import numpy as np
import pandas as pd
import hairline as hl

rng = np.random.default_rng(1)
cohort = pd.DataFrame({
    "arm": np.repeat(["Standard care", "Early mobilisation"], 40),
    "age": rng.normal(64, 12, 80).round(),
    "sex": rng.choice(["Female", "Male"], 80),
    "months": rng.exponential(20, 80).round(1),
    "died": rng.binomial(1, 0.4, 80),
})
study = hl.study(cohort, group="arm", time="months", event="died",
                 units={"age": "years", "months": "months"})

table_one = study.describe()     # Table 1: median (IQR) and n (%) per group
table_one.table                  # a data frame
age = study.compare("age")       # spread rows per group, Wilcoxon rank-sum
age.text                         # "Age (years), median (IQR): ... (Wilcoxon rank-sum, p = ...)."
age.numbers["test"]["p"]         # the unrounded p the text formats
survival = study.survival()      # Kaplan–Meier with numbers at risk and the log-rank test
hl.save(survival.figure, "survival")              # survival.pdf and survival.png
```

Printing a study lists its checks: missing values, duplicate ids, categories that differ only in case,
small groups, numeric columns without a unit. Errors stop the analysis; warnings name the fix. With `id=`,
`describe()`, `compare()` and `distribution()` refuse a variable with more than one row per id, so repeated
measurements are not counted as separate patients.

## Charts

Each chart is one call with the data and its column names, and returns a figure in the hairline frame:
`bars`, `scatter`, `timeseries`, `spread`, `raincloud`, `ridgeline`, `kaplan_meier`, `forest`, `dotplot`,
`funnel`, `correlation`, `donut`, `partition`, `sankey`, `chord`, `arcs`, `venn`, `prisma` and
`risk_of_bias`.

```python
admissions = pd.DataFrame({"diagnosis": ["Sepsis", "Sepsis", "Trauma", "Cardiac", "Cardiac"],
                           "sex": ["Female", "Male", "Male", "Female", "Male"]})
figure = hl.bars(admissions, "diagnosis", by="sex", subtitle="Admissions, 2025")
hl.save(figure, "admissions", formats=["pdf", "png", "svg", "html"])
```

For anything else, `hl.figure()` gives the same frame around your own matplotlib axes:

```python
figure = hl.figure("Lactate falls after admission", subtitle="Mean per day", size="single")
figure.ax.plot([0, 1, 2, 3], [4.1, 3.2, 2.6, 2.2], label="All patients")
figure.y_title("mmol/l")
hl.save(figure, "lactate")
```

## Colours

Groups take a palette's colours in order, so two groups always get the same two colours and a group keeps its
colour in every chart. `hl.palettes()` lists the six palettes, the purpose sets (two groups, greyscale print,
risk of bias) and the ramps for amounts; `hl.swatches()` draws them; `hl.use(palette="calm")` changes the
default; `hl.use(colors={"Unit B": "#e79d01"})` pins a colour to a name; `hl.colormap("blues")` gives a ramp
to your own matplotlib plots. `help(hairline.palettes)` has the details.

## Files

`save()` writes PDF (fonts embedded), PNG and TIFF (600 dpi by default), SVG (text kept as text) and
self-contained interactive HTML with tooltips. Files carry the figure's title and subtitle as their
description, and no timestamps: the same figure gives the same bytes again.

## Design

- `hl.use(brand="_brand.yml")` applies an institution's colours, fonts and sizes from a
  [brand.yml](https://posit-dev.github.io/brand-yml/) file; several files layer from institution to document.
- `hl.use(colors={"Unit B": "#e79d01"})` pins a colour to a name across every chart.
- Palettes are checked for colour-vision separation and contrast; `hl.check_palette()` reports the numbers.
- `hl.use(scheme="dark", accent="#0b6e4f")` draws on a dark surface with an accent for single series.

## Gallery

More figures, Python and R side by side, and the colour guide: [https://github.com/schradern/hairline](https://github.com/schradern/hairline).

![The same figure in Python and R](https://raw.githubusercontent.com/schradern/hairline/main/docs/images/parity.png)

## Author

Nikolas Schrader (<hi@nikolasschrader.com>), ORCID [0009-0001-4616-3804](https://orcid.org/0009-0001-4616-3804).

## How to cite

If hairline helped you make the figures in your work, please cite it; `hl.citation()` gives the reference
and `hl.citation("bibtex")` this entry:

```bibtex
@Manual{schrader2026hairline,
  title = {hairline: Clean, Predictable Figures for Medical and Data Science},
  author = {Nikolas Schrader},
  year = {2026},
  note = {Python package version 0.1.0},
  doi = {10.5281/zenodo.23456212},
}
```

## Licence

MIT. The bundled Hairline Sans font is a modified Public Sans (SIL Open Font License 1.1).
