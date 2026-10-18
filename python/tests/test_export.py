import shutil
import subprocess

import pytest
from PIL import Image

import hairline as hl
from hairline.export import figure_alt

TITLE = "Survival after ICU discharge"
DESCRIPTION = "Survival after ICU discharge. Kaplan–Meier estimate"


def sample_figure(subtitle="Kaplan–Meier estimate"):
    figure = hl.figure(TITLE, subtitle=subtitle, caption="Synthetic data")
    figure.ax.plot([0, 6, 12, 18], [1.0, 0.8, 0.65, 0.5], label="Standard care")
    figure.legend()
    return figure


def test_default_outputs(tmp_path):
    paths = hl.save(sample_figure(), tmp_path / "nested" / "survival")
    assert [path.suffix for path in paths] == [".pdf", ".png"]
    assert all(path.exists() for path in paths)
    with Image.open(paths[1]) as image:
        assert image.info["dpi"] == pytest.approx((600, 600), abs=0.5)


def test_pdf_embeds_font_and_has_no_timestamp(tmp_path):
    pdf = hl.save(sample_figure(), tmp_path / "f", formats=["pdf"])[0].read_bytes()
    assert b"/FontFile2" in pdf and b"HairlineSans" in pdf
    assert b"CreationDate" not in pdf and b"Producer" not in pdf


def test_svg_keeps_text_as_text(tmp_path):
    svg = hl.save(sample_figure(), tmp_path / "f", formats=["svg"])[0].read_text()
    assert "Survival after ICU discharge" in svg and "<dc:date>" not in svg


def test_byte_stable(tmp_path):
    first = hl.save(sample_figure(), tmp_path / "a", formats=["pdf", "svg"])
    second = hl.save(sample_figure(), tmp_path / "b", formats=["pdf", "svg"])
    assert all(a.read_bytes() == b.read_bytes() for a, b in zip(first, second, strict=True))


def test_unknown_format_writes_nothing(tmp_path):
    with pytest.raises(ValueError, match="unknown format 'jpeg'.*pdf, png, svg, tiff"):
        hl.save(sample_figure(), tmp_path / "out" / "f", formats=["png", "jpeg"])
    assert not (tmp_path / "out").exists()


def test_tiff_lzw(tmp_path):
    path = hl.save(sample_figure(), tmp_path / "f", formats=["tiff"])[0]
    with Image.open(path) as image:
        assert image.info["compression"] == "tiff_lzw" and image.info["dpi"] == pytest.approx((600, 600), abs=0.5)


def test_transparent_background(tmp_path):
    path = hl.save(sample_figure(), tmp_path / "f", formats=["png"], dpi=100, background="transparent")[0]
    with Image.open(path) as image:
        assert image.getpixel((1, 1))[3] == 0


def test_plain_matplotlib_figure_is_accepted(tmp_path):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([1, 2], [3, 4])
    assert hl.save(fig, tmp_path / "plain", formats=["png"], dpi=72)[0].exists()


def test_files_are_named_by_title_and_subtitle(tmp_path):
    pdf, png, svg = hl.save(sample_figure(), tmp_path / "named", formats=["pdf", "png", "svg"])
    assert f"/Title ({TITLE})".encode() in pdf.read_bytes()
    with Image.open(png) as image:
        assert (image.text["Title"], image.text["Description"]) == (TITLE, DESCRIPTION)
    assert f"<title>{TITLE}</title><desc>{DESCRIPTION}</desc>" in svg.read_text(encoding="utf-8")


def test_svg_name_is_escaped(tmp_path):
    svg = hl.save(sample_figure("Dose < 5 & > 1"), tmp_path / "escaped", formats=["svg"])[0]
    assert "<desc>Survival after ICU discharge. Dose &lt; 5 &amp; &gt; 1</desc>" in svg.read_text(encoding="utf-8")


@pytest.mark.skipif(shutil.which("pdfinfo") is None, reason="poppler's pdfinfo is not installed")
def test_pdf_readers_see_the_title_and_subject(tmp_path):
    pdf = hl.save(sample_figure(), tmp_path / "read", formats=["pdf"])[0]
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, check=True).stdout
    assert f"Title:           {TITLE}" in info and "Subject:         " + DESCRIPTION in info
    assert "Producer" not in info and "CreationDate" not in info


def test_alt_text_leaves_out_an_empty_subtitle_as_in_r():
    assert figure_alt(sample_figure("")) == TITLE
    assert figure_alt(hl.figure("", subtitle="Weekly counts")) == "Weekly counts"


def test_a_failed_write_names_the_underlying_error(tmp_path, monkeypatch):
    def failing_write(*arguments):
        raise KeyError(400)

    monkeypatch.setattr("hairline.export.write_one", failing_write)
    with pytest.raises(RuntimeError, match=r"failed: KeyError: 400$"):
        hl.save(sample_figure(), tmp_path / "broken", formats=["svg"])
    assert not list(tmp_path.iterdir())

