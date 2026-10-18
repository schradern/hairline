import io
import json

import pytest

import hairline as hl
from hairline import host


@pytest.fixture
def context(tmp_path, monkeypatch):
    def write(**values):
        content = {"version": 1, "host": "editor", "output": "pdf", "width_mm": 150, "figure_dir": str(tmp_path / "f"),
                   "design": {"font": "Hairline Sans"}, "dpi": 144, **values}
        path = tmp_path / f"context-{len(list(tmp_path.glob('context-*')))}.json"
        path.write_text(json.dumps(content))
        monkeypatch.setenv(host.ENVIRONMENT, str(path))
        return path
    yield write
    monkeypatch.delenv(host.ENVIRONMENT, raising=False)
    host._state.update(path=None, context=None)


def test_context_sets_the_default_width_and_the_hand_off_writes_files_and_manifest(context, tmp_path):
    context()
    hl.use(brand=False)
    figure = hl.figure("Lactate by unit", subtitle="Admissions 2025")
    figure.ax.plot([0, 1], [0, 1])
    assert figure.figure.get_size_inches()[0] * 25.4 == pytest.approx(150)
    width = hl.figure("Explicit", width_mm=80).figure.get_size_inches()[0] * 25.4
    assert width == pytest.approx(80)
    figure.figure.savefig(io.BytesIO(), format="png", dpi=144, bbox_inches="tight")
    figure.figure.savefig(io.BytesIO(), format="png")
    entries = json.loads((tmp_path / "f" / host.MANIFEST).read_text())
    assert len(entries) == 1
    assert set(entries[0]["files"]) == {"pdf", "png"} and entries[0]["width_mm"] == pytest.approx(150)
    assert entries[0]["alt"] == "Lactate by unit. Admissions 2025"


def test_bad_context_warns_once_and_continues(context, tmp_path, monkeypatch):
    path = tmp_path / "broken.json"
    path.write_text("{not json")
    monkeypatch.setenv(host.ENVIRONMENT, str(path))
    with pytest.warns(UserWarning, match="not valid JSON"):
        assert host.host_context() is None
    figure = hl.figure("Still works")
    assert figure.figure.get_size_inches()[0] * 25.4 == pytest.approx(120)


def test_html_output_writes_svg_and_explicit_arguments_win(context):
    context(output="html", locale="de")
    settings = hl.use(brand=False, locale="en")
    assert settings.locale == "en"
    assert hl.use(brand=False).locale == "de"
    assert host.FORMATS[host.host_context().output] == ("svg", "png")
