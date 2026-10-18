import pytest

import hairline as hl

BIBTEX = """@Manual{schrader2026hairline,
  title = {hairline: Clean, Predictable Figures for Medical and Data Science},
  author = {Nikolas Schrader},
  year = {2026},
  note = {Python package version 0.1.0},
  doi = {10.5281/zenodo.23456212},
}"""


def test_citation_text_matches_the_r_package_wording():
    assert hl.citation() == ("Schrader N (2026). hairline: Clean, Predictable Figures for Medical and Data "
                             "Science. Python package version 0.1.0. doi:10.5281/zenodo.23456212")


def test_citation_bibtex_has_the_same_shape_as_in_r():
    assert hl.citation("bibtex") == BIBTEX


def test_unknown_citation_style_is_named():
    with pytest.raises(ValueError, match="unknown citation style 'apa'; use text or bibtex"):
        hl.citation("apa")
