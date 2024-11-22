from pathlib import Path

from cse140l.digital.stats import CircuitStats
from cse140l.digital.svg import SVGExport
from cse140l.digital.tests import Tests


class Digital:
    def __init__(self, jar_file: Path) -> None:
        self.jar_file = jar_file
        self.cmd = ["java", "-cp", str(self.jar_file), "CLI"]

        self.svg = SVGExport(self.cmd)
        self.test = Tests(self.cmd)
        self.stats = CircuitStats(self.cmd)
