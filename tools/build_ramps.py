"""Compute the sequential and diverging ramps and store their hex values in the tokens."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from hairline.color.ramps import diverging_ramp, sequential_ramp

REPO = Path(__file__).resolve().parents[1]

TOKENS = REPO / "tokens" / "hairline.json"


def main() -> int:
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    definition = tokens["ramp_definitions"]
    ramps = {name: sequential_ramp(hue, definition) for name, hue in definition["sequential"].items()}
    ramps |= {name: diverging_ramp(*hues, definition) for name, hues in definition["diverging"].items()}
    tokens["ramps"] = ramps
    TOKENS.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
