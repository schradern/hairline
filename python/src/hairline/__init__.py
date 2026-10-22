"""hairline: clean, predictable figures for medical and data science."""

import importlib
import sys
import types
from typing import TYPE_CHECKING

from hairline.brand import brand_report, load_brand
from hairline.citation import citation
from hairline.color.check import PaletteReport, check_palette
from hairline.entities import color, colors
from hairline.errors import HairlineLayoutError
from hairline.export import save
from hairline.figure import HairlineFigure, figure, frame
from hairline.numbers import format_interval, format_number, format_percent
from hairline.palettes import colormap, palette, palettes, ramp
from hairline.settings import Settings, current_settings, use
from hairline.tokens import load_tokens

# Chart and study functions load on first use, so a figure drawn with figure() and save() never imports pandas.
LAZY_NAMES = {
    **{name: f"hairline.charts.{name}" for name in (
        "arcs", "bars", "chord", "correlation", "donut", "dotplot", "forest", "funnel", "kaplan_meier", "partition",
        "prisma", "raincloud", "ridgeline", "risk_of_bias", "sankey", "scatter", "spread", "swatches", "timeseries",
        "venn")},
    "Result": "hairline.study", "Study": "hairline.study", "study": "hairline.study",
}

if TYPE_CHECKING:
    from hairline.charts.arcs import arcs
    from hairline.charts.bars import bars
    from hairline.charts.chord import chord
    from hairline.charts.correlation import correlation
    from hairline.charts.donut import donut
    from hairline.charts.dotplot import dotplot
    from hairline.charts.forest import forest
    from hairline.charts.funnel import funnel
    from hairline.charts.kaplan_meier import kaplan_meier
    from hairline.charts.partition import partition
    from hairline.charts.prisma import prisma
    from hairline.charts.raincloud import raincloud
    from hairline.charts.ridgeline import ridgeline
    from hairline.charts.risk_of_bias import risk_of_bias
    from hairline.charts.sankey import sankey
    from hairline.charts.scatter import scatter
    from hairline.charts.spread import spread
    from hairline.charts.swatches import swatches
    from hairline.charts.timeseries import timeseries
    from hairline.charts.venn import venn
    from hairline.study import Result, Study, study


def __getattr__(name: str):
    if name not in LAZY_NAMES:
        raise AttributeError(f"module 'hairline' has no attribute {name!r}")
    value = getattr(importlib.import_module(LAZY_NAMES[name]), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(LAZY_NAMES))


class HairlineModule(types.ModuleType):
    """Keeps `hairline.study` the function: importing the subpackage of the same name would otherwise replace it."""

    def __setattr__(self, name: str, value) -> None:
        if name in LAZY_NAMES and isinstance(value, types.ModuleType):
            return
        super().__setattr__(name, value)


sys.modules[__name__].__class__ = HairlineModule

__all__ = [
    "HairlineFigure", "HairlineLayoutError", "PaletteReport", "Result", "Settings", "Study", "arcs", "bars",
    "brand_report", "check_palette", "chord", "citation", "color", "colormap", "colors", "correlation",
    "current_settings", "donut", "dotplot", "figure", "forest", "format_interval", "format_number", "format_percent",
    "frame", "funnel", "kaplan_meier", "load_brand", "load_tokens", "palette", "palettes", "partition", "prisma",
    "raincloud", "ramp", "ridgeline", "risk_of_bias", "sankey", "save", "scatter", "spread", "study", "swatches",
    "timeseries", "use", "venn",
]
__version__ = "0.2.0.dev0"


def _apply_host_context() -> None:
    """Inside a host document (HAIRLINE_HOST_CONTEXT set), start from the document's context; a style that cannot
    be applied (a broken brand file) is warned about instead of stopping the import."""
    import warnings

    from hairline.host import host_context
    if host_context() is not None:
        try:
            use()
        except ValueError as error:
            warnings.warn(f"hairline: the host context's style could not be applied ({error}); using the defaults",
                          UserWarning, stacklevel=2)


_apply_host_context()
