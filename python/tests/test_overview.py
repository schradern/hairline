import subprocess
import sys


def test_overview_names_a_missing_gallery_image(repo_root, tmp_path):
    result = subprocess.run([sys.executable, "tools/overview.py", "--gallery", str(tmp_path)], cwd=repo_root,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "donut_discharge.png is missing" in result.stderr
