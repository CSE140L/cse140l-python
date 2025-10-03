import subprocess
from typing import List


class DigitalModule:
    def __init__(self, cmd: List[str]):
        self.cmd = cmd

    def _run(self, command: List[str]) -> subprocess.CompletedProcess:
        process = subprocess.run(self.cmd + command, capture_output=True)
        return process