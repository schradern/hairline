"""Build the bundled font: Public Sans with tabular figures as default, renamed and subset.

Public Sans (SIL OFL 1.1, no Reserved Font Name) is modified here, so the build ships under its own
family name, "Hairline Sans". That also avoids clashing with a system-installed Public Sans.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "tokens" / "fonts"
RELEASE = "v2.001"
URL = f"https://github.com/uswds/public-sans/releases/download/{RELEASE}/public-sans-{RELEASE}.zip"
FAMILY = "Hairline Sans"
STYLES = {"400": "Regular", "500": "Medium", "600": "SemiBold",
          "400i": "Italic", "500i": "MediumItalic", "600i": "SemiBoldItalic"}
EXTRA_CHARACTERS = "−≥≤×·→←ρτ²³±√∞≈≠°µ…–—‘’“”„‹›«»•€"
UNICODE_RANGES = [(0x20, 0x7E), (0xA0, 0x17F), (0x2000, 0x206F)]


def download_release() -> zipfile.ZipFile:
    with urllib.request.urlopen(URL, timeout=60) as response:
        return zipfile.ZipFile(io.BytesIO(response.read()))


def extract_style(archive: zipfile.ZipFile, style: str, folder: Path) -> Path:
    member = f"fonts/ttf/PublicSans-{style}.ttf"
    try:
        data = archive.read(member)
    except KeyError as error:
        raise RuntimeError(f"build_font: {member} missing from Public Sans {RELEASE}") from error
    path = folder / f"PublicSans-{style}.ttf"
    path.write_bytes(data)
    return path


def freeze_tabular(source: Path, target: Path) -> None:
    command = ["pyftfeatfreeze", "-f", "tnum", "-R", f"Public Sans/{FAMILY},PublicSans/HairlineSans",
               str(source), str(target)]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"build_font: freezing tnum failed for {source.name}: {result.stderr.strip()}")


def subset_font(path: Path) -> None:
    unicodes = {code for low, high in UNICODE_RANGES for code in range(low, high + 1)}
    unicodes |= {ord(character) for character in EXTRA_CHARACTERS}
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    font = TTFont(path)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    font.save(path)


def font_metrics(path: Path) -> dict[str, float | str]:
    font = TTFont(path)
    units = font["head"].unitsPerEm
    return {"family": FAMILY, "cap_height": round(font["OS/2"].sCapHeight / units, 4),
            "descender": round(abs(font["hhea"].descent) / units, 4),
            "ascender": round(font["hhea"].ascent / units, 4)}


def write_token_entry(files: dict[str, str]) -> None:
    tokens_path = REPO / "tokens" / "hairline.json"
    tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
    tokens["font"] = {"family": FAMILY, "source": f"Public Sans {RELEASE} (SIL OFL 1.1)", "files": files}
    tokens_path.write_text(json.dumps(tokens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    archive = download_release()
    (OUTPUT / "OFL.txt").write_bytes(archive.read("OFL.txt"))
    files: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as scratch:
        for key, style in STYLES.items():
            target = OUTPUT / f"HairlineSans-{style}.ttf"
            freeze_tabular(extract_style(archive, style, Path(scratch)), target)
            subset_font(target)
            files[key] = target.name
    (OUTPUT / "metrics.json").write_text(json.dumps(font_metrics(OUTPUT / "HairlineSans-Regular.ttf"), indent=2) + "\n")
    write_token_entry(files)
    return 0


if __name__ == "__main__":
    sys.exit(main())
