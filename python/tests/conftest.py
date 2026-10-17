from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def repo_root() -> Path:
    return REPO


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch, tmp_path):
    """Every test starts from defaults, outside any project that might hold a _brand.yml."""
    import hairline.settings as settings_module
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("HAIRLINE_HOST_CONTEXT", raising=False)
    settings_module.reset()
    matplotlib.rcdefaults()
    yield
    import matplotlib.pyplot as plt
    plt.close("all")
    settings_module.reset()
    matplotlib.rcdefaults()
