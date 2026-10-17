import json

import pytest
from fontTools.ttLib import TTFont

from hairline.tokens import load_tokens

STYLES = ["Regular", "Medium", "SemiBold", "Italic", "MediumItalic", "SemiBoldItalic"]


@pytest.fixture
def font_dir(repo_root):
    return repo_root / "tokens" / "fonts"


@pytest.mark.parametrize("style", STYLES)
def test_bundled_font_has_tabular_default(font_dir, style):
    font = TTFont(font_dir / f"HairlineSans-{style}.ttf")
    cmap, metrics = font.getBestCmap(), font["hmtx"]
    widths = {metrics[cmap[ord(digit)]][0] for digit in "0123456789"}
    assert len(widths) == 1


def test_metrics_and_token_entry(font_dir):
    metrics = json.loads((font_dir / "metrics.json").read_text())
    assert 0.6 < metrics["cap_height"] < 0.8 and 0.1 < metrics["descender"] < 0.3
    assert load_tokens()["font"]["family"] == metrics["family"] == "Hairline Sans"
    assert set(load_tokens()["font"]["files"]) == {"400", "500", "600", "400i", "500i", "600i"}


def test_font_files_are_small(font_dir):
    assert sum(path.stat().st_size for path in font_dir.glob("*.ttf")) < 1_500_000


def test_licence_shipped(font_dir):
    assert "SIL OPEN FONT LICENSE" in (font_dir / "OFL.txt").read_text()
