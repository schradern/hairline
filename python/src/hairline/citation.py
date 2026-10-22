"""citation(): how to cite hairline, worded as the R package's citation("hairline") is."""

from __future__ import annotations

AUTHOR, INITIALS, YEAR, KEY = "Nikolas Schrader", "Schrader N", "2026", "schrader2026hairline"
DOI = "10.5281/zenodo.23456211"
TITLE = "hairline: Clean, Predictable Figures for Medical and Data Science"
STYLES = ("text", "bibtex")


def citation(style: str = "text") -> str:
    """The reference for the methods section ("text") or a BibTeX entry ("bibtex")."""
    from hairline import __version__
    if style not in STYLES:
        raise ValueError(f"hairline: unknown citation style {style!r}; use {' or '.join(STYLES)}")
    note = f"Python package version {__version__}"
    if style == "text":
        return f"{INITIALS} ({YEAR}). {TITLE}. {note}. doi:{DOI}"
    fields = {"title": TITLE, "author": AUTHOR, "year": YEAR, "note": note, "doi": DOI}
    return "\n".join([f"@Manual{{{KEY},", *(f"  {name} = {{{value}}}," for name, value in fields.items()), "}"])
