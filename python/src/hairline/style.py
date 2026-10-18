"""matplotlib rcParams derived from hairline settings and tokens."""

from __future__ import annotations

from cycler import cycler

from hairline.settings import Settings, role_size
from hairline.tokens import load_tokens


def text_params(settings: Settings) -> dict[str, object]:
    neutral = settings.neutral
    label = role_size(settings, "label")
    return {
        "font.family": [settings.font], "font.size": settings.base_size, "text.color": neutral["ink"],
        "axes.titlesize": role_size(settings, "panel"), "axes.titleweight": 600,
        "axes.titlecolor": neutral["ink"], "axes.titlelocation": "left", "axes.labelsize": label,
        "axes.labelcolor": neutral["muted"], "xtick.labelsize": label, "ytick.labelsize": label,
        "xtick.color": neutral["faint"], "ytick.color": neutral["faint"], "legend.fontsize": label,
        "legend.labelcolor": neutral["muted"], "legend.frameon": False,
        "figure.titlesize": role_size(settings, "title"), "figure.titleweight": 600,
    }


def line_params(settings: Settings) -> dict[str, object]:
    lines, neutral, base = load_tokens()["lines"], settings.neutral, settings.base_size
    return {
        "axes.spines.left": False, "axes.spines.right": False, "axes.spines.top": False,
        "axes.spines.bottom": True, "axes.edgecolor": neutral["axis"], "axes.linewidth": lines["axis"] * base,
        "axes.grid": True, "axes.grid.axis": "y", "axes.axisbelow": True, "grid.color": neutral["grid"],
        "grid.linewidth": lines["grid"] * base, "xtick.major.size": 0, "ytick.major.size": 0,
        "xtick.minor.size": 0, "ytick.minor.size": 0, "lines.linewidth": lines["data"] * base,
        "lines.markersize": 2 * lines["point_radius"] * base, "patch.linewidth": 0,
        "axes.prop_cycle": cycler(color=list(settings.palette)),
    }


def output_params(settings: Settings) -> dict[str, object]:
    transparent = settings.background == "transparent"
    surface = "none" if transparent else settings.background
    return {
        "figure.facecolor": surface, "axes.facecolor": surface, "savefig.facecolor": surface,
        "savefig.transparent": transparent, "savefig.pad_inches": 0, "pdf.fonttype": 42, "ps.fonttype": 42,
        "svg.fonttype": "none", "svg.hashsalt": "hairline",
    }


def rcparams_for(settings: Settings) -> dict[str, object]:
    """All rcParams hairline sets; applied by `use()`."""
    return {**text_params(settings), **line_params(settings), **output_params(settings)}
