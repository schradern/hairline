"""Access to the shared design tokens bundled with the package."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache(maxsize=1)
def load_tokens() -> dict[str, Any]:
    """Return the design tokens shared by the Python and R packages."""
    source = resources.files("hairline") / "data" / "tokens.json"
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"hairline: bundled tokens missing at {source}; reinstall the package") from error
