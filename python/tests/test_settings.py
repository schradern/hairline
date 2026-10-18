import warnings

import matplotlib
import matplotlib.pyplot as plt
import pytest

import hairline as hl
from hairline.settings import current_settings, role_size
from hairline.tokens import load_tokens


def test_use_defaults():
    settings = hl.use()
    assert settings.base_size == 9 and settings.palette_name == "daylight" and settings.locale == "en"
    assert matplotlib.rcParams["font.family"] == [settings.font] == ["Hairline Sans"]
    assert matplotlib.rcParams["pdf.fonttype"] == 42 and matplotlib.rcParams["svg.fonttype"] == "none"
    assert current_settings() is settings


def test_role_sizes():
    settings = hl.use(base_size=10, sizes={"title": 14})
    assert role_size(settings, "title") == 14 and role_size(settings, "label") == pytest.approx(8.0)
    assert settings.base_size_explicit


def test_unknown_role_size_key():
    with pytest.raises(ValueError, match="unknown text role 'heading'.*caption, label, panel, subtitle, title"):
        hl.use(sizes={"heading": 12})


def test_missing_font_warns_once():
    with pytest.warns(UserWarning, match="font 'Definitely Missing Sans' is not installed"):
        settings = hl.use(font="Definitely Missing Sans")
    assert settings.font == load_tokens()["font"]["family"]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        hl.use(font="Definitely Missing Sans")


def test_palette_by_name_and_custom():
    assert hl.use(palette="lagoon").palette[0] == "#0c71d1"
    custom = hl.use(palette=["#112233", "#445566"])
    assert custom.palette_name == "custom" and hl.palette() == ["#112233", "#445566"]


def test_axes_style():
    hl.use()
    _, ax = plt.subplots()
    assert not ax.spines["top"].get_visible() and not ax.spines["left"].get_visible()
    assert ax.spines["bottom"].get_visible()
    assert matplotlib.rcParams["axes.titlelocation"] == "left"
    assert matplotlib.rcParams["axes.grid.axis"] == "y"
    assert matplotlib.rcParams["ytick.major.size"] == 0
    assert matplotlib.rcParams["lines.linewidth"] == pytest.approx(0.14 * 9)
    plt.close("all")


def test_transparent_background():
    hl.use(background="transparent")
    assert matplotlib.rcParams["savefig.transparent"] is True


def test_locale_flows_into_number_formatting():
    hl.use(locale="de")
    assert hl.format_percent(0.614) == "61,4 %"


def test_plain_matplotlib_after_use_finds_the_bundled_font(tmp_path, caplog):
    hl.use()
    fig, ax = plt.subplots()
    ax.set_title("Bundled font")
    with caplog.at_level("WARNING", logger="matplotlib.font_manager"):
        fig.savefig(tmp_path / "plain.png")
    assert not [record for record in caplog.records if "not found" in record.message]
    plt.close(fig)


def test_supporting_elements_recede():
    from hairline.layout.styles import header_styles
    settings = hl.use()
    styles = header_styles(settings)
    assert role_size(settings, "label") == pytest.approx(7.2) and role_size(settings, "caption") == pytest.approx(7.2)
    assert styles["stat_label"]["color"] == settings.neutral["faint"]
    assert styles["stat_value"]["color"] == settings.neutral["muted"] and styles["stat_value"]["weight"] == 400
    assert styles["key_value"]["color"] == settings.neutral["ink"] and styles["key_value"]["weight"] == 600
    assert settings.neutral["grid"] == "#eef0f2"
    assert matplotlib.rcParams["grid.linewidth"] == pytest.approx(0.05 * 9)


def test_accent_colours_a_lone_series_and_dark_swaps_the_neutrals():
    import pandas as pd

    from hairline.marks import lone_color
    settings = hl.use(brand=False, scheme="dark", accent="#2D1B69")
    assert settings.neutral == hl.load_tokens()["neutral_dark"] and settings.background == settings.neutral["surface"]
    assert settings.accent == "#2d1b69" and lone_color() != "#2d1b69"
    data = pd.DataFrame({"diagnosis": ["Sepsis", "Trauma", "Sepsis"]})
    figure = hl.bars(data, "diagnosis")
    from matplotlib.colors import to_hex
    assert to_hex(figure.ax.patches[0].get_facecolor()) == lone_color()
    grouped = hl.bars(data.assign(sex=["F", "M", "F"]), "diagnosis", by="sex")
    assert to_hex(grouped.ax.patches[0].get_facecolor()) == hl.palette()[0]
    with pytest.raises(ValueError, match="scheme 'dim' must be 'light' or 'dark'"):
        hl.use(brand=False, scheme="dim")
    hl.use(brand=False)
