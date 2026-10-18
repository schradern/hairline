import subprocess
import sys

from hairline.tokens import load_tokens

SECTIONS = {"type", "spacing", "lines", "neutral", "palettes", "sets", "ramps", "sizes", "locales", "checks", "font"}


def test_tokens_have_all_sections():
    tokens = load_tokens()
    assert set(tokens) >= SECTIONS
    assert tokens["palettes"]["daylight"] == [
        "#0a6ddd", "#de4642", "#e79d01", "#019a98", "#f07202", "#06b1f7", "#06a141", "#8264e7",
    ]
    assert tokens["spacing"]["panel_rows"] == 2.25


def test_package_copy_matches_source(repo_root):
    result = subprocess.run([sys.executable, "tools/sync_tokens.py", "--check"], cwd=repo_root, check=False)
    assert result.returncode == 0
