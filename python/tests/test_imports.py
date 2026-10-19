import subprocess
import sys

BASIC_FIGURE = """
import sys
import hairline as hl
figure = hl.figure("Power by sample size", size="onehalf")
figure.ax.plot([40, 80, 120], [0.05, 0.42, 0.896], label="Power")
figure.reference(y=0.9, label="Target 90%")
figure.percent_axis(0, digits=1)
figure.panel_header(0, "Two-sided test")
hl.save(figure, sys.argv[1], formats=["svg", "html"])
print("pandas" in sys.modules)
"""


def test_a_basic_figure_is_drawn_and_saved_without_pandas(tmp_path):
    result = subprocess.run([sys.executable, "-c", BASIC_FIGURE, str(tmp_path / "power")], capture_output=True,
                            text=True, check=True)
    assert result.stdout.strip() == "False"
    assert (tmp_path / "power.svg").exists() and (tmp_path / "power.html").exists()


def test_chart_functions_load_on_first_use():
    script = "import hairline as hl; print(callable(hl.bars), 'bars' in dir(hl))"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "True True"
