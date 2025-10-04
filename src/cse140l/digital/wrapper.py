import subprocess
from pathlib import Path
from subprocess import Popen

from cse140l.digital.stats import CircuitStats
from cse140l.digital.images import ImageExport
from cse140l.digital.tests import Tests


class Digital:
    def __init__(self, jar_file: Path) -> None:
        self.jar_file = jar_file
        self.cmd = ["java", "-jar", str(self.jar_file)]
        self.cli_cmd = ["java", "-cp", str(self.jar_file), "CLI"]

        self.img = ImageExport(self.cli_cmd)
        self.test = Tests(self.cli_cmd)
        self.stats = CircuitStats(self.cli_cmd)


    def launch(self, circuit: Path = None) -> Popen[bytes]:
        process = subprocess.Popen(self.cmd + [str(circuit)])
        return process
