"""hairline: clean, predictable figures for medical and data science."""

from hairline.charts.bars import bars
from hairline.charts.donut import donut
from hairline.charts.dotplot import dotplot
from hairline.charts.forest import forest
from hairline.charts.kaplan_meier import kaplan_meier
from hairline.charts.partition import partition
from hairline.charts.raincloud import raincloud
from hairline.charts.sankey import sankey
from hairline.charts.timeseries import timeseries
from hairline.color.check import PaletteReport, check_palette
from hairline.entities import color, colors
from hairline.errors import HairlineLayoutError
from hairline.export import save
from hairline.figure import HairlineFigure, figure, frame
from hairline.numbers import format_interval, format_number, format_percent
from hairline.palettes import palette, ramp
from hairline.settings import Settings, current_settings, use
from hairline.tokens import load_tokens

__all__ = [
    "HairlineFigure", "HairlineLayoutError", "PaletteReport", "Settings", "bars", "check_palette", "color", "colors",
    "current_settings", "donut", "dotplot", "figure", "forest", "format_interval", "format_number", "format_percent",
    "frame", "kaplan_meier", "load_tokens", "palette", "partition", "raincloud", "ramp", "sankey", "save",
    "timeseries", "use",
]
__version__ = "0.1.0"
