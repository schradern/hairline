"""Compute the sequential and diverging ramps and store their hex values in the tokens."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from hairline.color.space import oklch_to_hex

REPO = Path(__file__).resolve().parents[1]

TOKENS = REPO / "tokens" / "hairline.json"


def sequential(hue: float | None, definition: dict) -> list[str]:
    steps = definition["steps"]
    light, dark = definition["lightness"]
    colors = []
    for index in range(steps):
        lightness = light + (dark - light) * index / (steps - 1)
        envelope = 0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.7 * index / (steps - 1)))
        chroma = 0.0 if hue is None else definition["chroma_peak"] * envelope
        colors.append(oklch_to_hex(lightness, chroma, hue or 0.0))
    return colors


def diverging(low_hue: float, high_hue: float, definition: dict) -> list[str]:
    low, high = sequential(low_hue, definition), sequential(high_hue, definition)
    return list(reversed(low[1:])) + [definition["midpoint"]] + high[1:]


def main() -> int:
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    definition = tokens["ramp_definitions"]
    ramps = {name: sequential(hue, definition) for name, hue in definition["sequential"].items()}
    ramps |= {name: diverging(*hues, definition) for name, hues in definition["diverging"].items()}
    tokens["ramps"] = ramps
    TOKENS.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
