# hairline

Clean, predictable figures for medical and data science, as a pair of packages that draw the same figures:

- [`python/`](python/README.md): the Python package, on matplotlib.
- [`r/`](r/README.md): the R package, on ggplot2.

Both read one set of design tokens (`tokens/hairline.json`): type scale, spacing, line widths, palettes and
the bundled font. A figure drawn in Python and the same figure drawn in R have the same frame, to within a
point.

## Layout

| Folder | Holds |
|---|---|
| `tokens/` | the shared design tokens, font, interactive assets and test fixtures |
| `python/`, `r/` | the two packages; `tools/sync_tokens.py` copies the tokens into each |
| `gallery/` | one script per figure in each language, on synthetic data from `gallery/data/make_data.py` |
| `brands/example/` | an example brand file |
| `tools/` | token sync, fixture builders, the font build and the parity check |

## Working on it

```bash
python3 tools/sync_tokens.py
```

```bash
cd python && uv run --with lifelines pytest
```

```bash
cd r && Rscript -e 'devtools::test()'
```

```bash
cd python && uv run python ../tools/parity.py
```

`tools/parity.py` runs the gallery in both languages and compares the frame positions and the interactive
targets of every figure. Install the R package first (`R CMD INSTALL r`).

## Author

Nikolas Schrader (<hi@nikolasschrader.com>).

## How to cite

`CITATION.cff` holds the reference (GitHub shows it as "Cite this repository"); in R, `citation("hairline")`
prints it.

## Licence

MIT. The bundled Hairline Sans font is a modified Public Sans (SIL Open Font License 1.1).
