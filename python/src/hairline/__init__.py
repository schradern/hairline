"""hairline: clean, predictable figures for medical and data science."""

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
from hairline.charts.timeseries import timeseries
from hairline.charts.venn import venn
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
    "HairlineFigure", "HairlineLayoutError", "PaletteReport", "Settings", "arcs", "bars", "check_palette", "chord",
    "color", "colors", "correlation", "current_settings", "donut", "dotplot", "figure", "forest", "format_interval",
    "format_number", "format_percent", "frame", "funnel", "kaplan_meier", "load_tokens", "palette", "partition",
    "prisma", "raincloud", "ramp", "ridgeline", "risk_of_bias", "sankey", "save", "scatter", "timeseries", "use",
    "venn",
]
__version__ = "0.1.0"
