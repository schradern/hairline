"""Study endpoints: describe a dataset once, then get each recurring analysis as one call
returning its figure, table, values and text."""

from hairline.study.checks import Finding
from hairline.study.model import Study, study
from hairline.study.result import Result

__all__ = ["Finding", "Result", "Study", "study"]
