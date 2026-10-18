"""Copy the shared tokens, fonts and fixtures into both packages, or check that the copies match."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOKENS = REPO / "tokens"
TARGETS = [
    (TOKENS / "hairline.json", REPO / "python/src/hairline/data/tokens.json"),
    (TOKENS / "hairline.json", REPO / "r/inst/tokens/hairline.json"),
    (REPO / "brands/example/_brand.yml", REPO / "r/tests/testthat/fixtures/example_brand.yml"),
    (REPO / "brands/example/units.yml", REPO / "r/tests/testthat/fixtures/example_units.yml"),
]
TREES = [
    (TOKENS / "fonts", REPO / "python/src/hairline/data/fonts"),
    (TOKENS / "fonts", REPO / "r/inst/fonts"),
    (TOKENS / "interactive", REPO / "python/src/hairline/data/interactive"),
    (TOKENS / "interactive", REPO / "r/inst/interactive"),
    (TOKENS / "fixtures", REPO / "python/tests/fixtures"),
    (TOKENS / "fixtures", REPO / "r/tests/testthat/fixtures"),
]


def planned_copies() -> list[tuple[Path, Path]]:
    copies = list(TARGETS)
    for source_dir, target_dir in TREES:
        files = [path for path in sorted(source_dir.rglob("*")) if path.is_file() and path.name != ".DS_Store"]
        copies += [(path, target_dir / path.relative_to(source_dir)) for path in files]
    return copies


def differing(copies: list[tuple[Path, Path]]) -> list[Path]:
    return [target for source, target in copies
            if not target.exists() or not filecmp.cmp(source, target, shallow=False)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 1 if any package copy differs from tokens/")
    copies = planned_copies()
    if parser.parse_args().check:
        stale = differing(copies)
        for path in stale:
            sys.stderr.write(f"sync_tokens: out of date: {path.relative_to(REPO)}\n")
        return 1 if stale else 0
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
