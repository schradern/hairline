import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="the parity check needs R with hairline installed")
def test_python_and_r_frames_agree_within_one_point(repo_root):
    result = subprocess.run([sys.executable, "tools/parity.py"], cwd=repo_root, capture_output=True, text=True,
                            check=False)
    assert result.returncode == 0, result.stderr
