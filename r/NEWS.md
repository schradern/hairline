# hairline 0.1.0

* First release.
* One frame for titles, legends, panels and captions around any ggplot (`theme_hairline()`), with the
  type scale, spacing and line widths of the shared design tokens.
* Nineteen charts, from bars and time series to Kaplan-Meier, forest, Sankey and PRISMA diagrams.
* `hl_study()` with endpoints for cohort description, group comparison, effects, survival and change over
  time; each returns a figure, a table, values and a sentence.
* Brands in the 'brand.yml' format, entity colours pinned to names, colour-vision checked palettes, light
  and dark schemes.
* `hl_save()` for PDF, PNG, TIFF, SVG and interactive HTML; files are named by the figure and carry no
  timestamps.
* Output matches the 'hairline' Python package.
