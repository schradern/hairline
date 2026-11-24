import base64

import matplotlib.pyplot as plt
import pandas as pd
import pytest

import hairline as hl
from hairline import notebook


def bars():
    return hl.bars(pd.DataFrame({"unit": ["A", "B"], "n": [3, 5]}), "unit", "n", title="Admissions")


def test_a_figure_shows_itself_as_a_png_at_its_own_size():
    figure = bars()
    data, metadata = figure._repr_mimebundle_()
    assert base64.b64decode(data["image/png"]).startswith(b"\x89PNG")
    width, height = figure.figure.get_size_inches()
    assert metadata["image/png"] == {"width": round(width * 96), "height": round(height * 96)}
    assert data["text/plain"].startswith("<hairline figure 'Admissions', ")


def test_a_result_shows_its_figure_sentence_and_table():
    study = hl.study(pd.DataFrame({"age": [61, 72, 55, 48], "sex": ["F", "M", "F", "M"]}),
                     units={"age": "years"})
    bundle = study.profile()._repr_mimebundle_()
    page = bundle["text/html"]
    assert page.startswith('<img src="data:image/png;base64,')
    assert page.index("<p>4 participants.</p>") < page.index("<table")


def test_figures_and_results_save_themselves(tmp_path):
    assert [path.name for path in bars().save(tmp_path / "admissions", formats=["png"])] == ["admissions.png"]
    study = hl.study(pd.DataFrame({"age": [61, 72, 55, 48]}), units={"age": "years"})
    paths = study.profile().save(tmp_path / "out" / "cohort", formats=["pdf"])
    assert [path.name for path in paths] == ["cohort.pdf", "cohort.csv"]
    assert pd.read_csv(paths[1], dtype=str).iloc[0].tolist() == ["n", "4"]


@pytest.mark.parametrize(("in_kernel", "listed"), [(True, False), (False, True)])
def test_only_a_notebook_kernel_keeps_figures_out_of_pyplots_display(monkeypatch, in_kernel, listed):
    monkeypatch.setattr(notebook, "in_notebook", lambda: in_kernel)
    figure = bars()
    assert (figure.figure.number in plt.get_fignums()) is listed
    plt.close("all")
