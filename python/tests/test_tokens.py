import subprocess
import sys

from hairline.tokens import load_tokens

SECTIONS = {"type", "spacing", "lines", "neutral", "palettes", "sets", "ramps", "sizes", "locales", "checks", "font"}


def test_tokens_have_all_sections():
    tokens = load_tokens()
    assert set(tokens) >= SECTIONS
    assert tokens["palettes"]["daylight"] == [
        "#2474cf", "#ef675a", "#b93780", "#53b0de", "#e8a628", "#00afa9", "#8362cd", "#44aa5a",
    ]
    assert tokens["spacing"]["panel_rows"] == 2.25


def test_package_copy_matches_source(repo_root):
    result = subprocess.run([sys.executable, "tools/sync_tokens.py", "--check"], cwd=repo_root, check=False)
    assert result.returncode == 0
