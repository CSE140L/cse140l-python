import subprocess
from pathlib import Path
from subprocess import Popen

from src.cse140l.digital.stats import CircuitStats
from src.cse140l.digital.svg import SVGExport
from src.cse140l.digital.tests import Tests


class Digital:
    def __init__(self, jar_file: Path) -> None:
        self.jar_file = jar_file
        self.cmd = ["java", "-jar", str(self.jar_file)]
        self.cli_cmd = ["java", "-cp", str(self.jar_file), "CLI"]

        self.svg = SVGExport(self.cli_cmd)
        self.test = Tests(self.cli_cmd)
        self.stats = CircuitStats(self.cli_cmd)


    def launch(self, circuit: Path = None) -> Popen[bytes]:
        process = subprocess.Popen(self.cmd + [str(circuit)])
        return process
