"""Sort and wrap the Python package's __all__ list to the line limit."""

import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parents[1] / "python" / "src" / "hairline" / "__init__.py"


def main() -> int:
    text = INIT.read_text()
    start = text.index("__all__ = [")
    end = text.index("]", start) + 1
    names = sorted(set(re.findall(r'"([^"]+)"', text[start:end])), key=lambda name: (name[0].islower(), name))
    lines, current = [], "    "
    for name in names:
        item = f'"{name}", '
        if len(current) + len(item) > 118:
            lines.append(current.rstrip())
            current = "    "
        current += item
    lines.append(current.rstrip())
    INIT.write_text(text[:start] + "__all__ = [\n" + "\n".join(lines) + "\n]" + text[end:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
