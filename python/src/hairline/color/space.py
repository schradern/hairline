"""Conversions between hex, sRGB, OKLab and OKLCH (Ottosson 2020)."""

from __future__ import annotations

import math
import re

HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
GAMUT_TOLERANCE = 1e-6


def parse_hex(color: str) -> tuple[float, float, float]:
    """Return sRGB channels in [0, 1] for a '#rrggbb' string."""
    if not isinstance(color, str) or not HEX_PATTERN.match(color):
        raise ValueError(f"hairline: {color!r} is not a 6-digit hex colour (expected '#rrggbb')")
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def to_gamma(channel: float) -> float:
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def linear_to_hex(red: float, green: float, blue: float) -> str:
    return "#" + "".join(f"{round(to_gamma(min(1.0, max(0.0, c))) * 255):02x}" for c in (red, green, blue))


def linear_to_oklab(red: float, green: float, blue: float) -> tuple[float, float, float]:
    long = math.cbrt(0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue)
    medium = math.cbrt(0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue)
    short = math.cbrt(0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue)
    return (0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short,
            1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short,
            0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short)


def oklab_to_linear(lightness: float, a: float, b: float) -> tuple[float, float, float]:
    long = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    medium = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    short = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
            -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
            -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short)


def hex_to_linear(color: str) -> tuple[float, float, float]:
    return tuple(to_linear(channel) for channel in parse_hex(color))


def hex_to_oklab(color: str) -> tuple[float, float, float]:
    return linear_to_oklab(*hex_to_linear(color))


def hex_to_oklch(color: str) -> tuple[float, float, float]:
    """Return (lightness, chroma, hue in degrees) for a hex colour."""
    lightness, a, b = hex_to_oklab(color)
    chroma = math.hypot(a, b)
    hue = math.degrees(math.atan2(b, a)) % 360 if chroma > 1e-9 else 0.0
    return lightness, chroma, hue


def in_gamut(linear: tuple[float, float, float]) -> bool:
    return all(-GAMUT_TOLERANCE <= channel <= 1 + GAMUT_TOLERANCE for channel in linear)


def oklch_to_linear(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    radians = math.radians(hue)
    return oklab_to_linear(lightness, chroma * math.cos(radians), chroma * math.sin(radians))


def oklch_to_hex(lightness: float, chroma: float, hue: float) -> str:
    """Convert OKLCH to hex; chroma is reduced by bisection when outside sRGB, keeping L and h."""
    linear = oklch_to_linear(lightness, chroma, hue)
    if not in_gamut(linear):
        low, high = 0.0, chroma
        for _ in range(40):
            middle = (low + high) / 2
            low, high = (middle, high) if in_gamut(oklch_to_linear(lightness, middle, hue)) else (low, middle)
        linear = oklch_to_linear(lightness, low, hue)
    return linear_to_hex(*linear)
