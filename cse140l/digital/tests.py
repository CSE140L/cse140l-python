import re
from typing import List
from pathlib import Path
from cse140l.digital.util import DigitalModule
from cse140l.gradescope.test_result import TestStatus

class TestOutput:
    def __init__(self, name: str, outcome: TestStatus, output: str):
        self.name = name
        self.outcome = outcome
        self.signals: List[str] = []
        self.steps: List[dict] = []
        self._generate_table(output)

    def _generate_table(self, output: str) -> None:
        if self.outcome != TestStatus.FAILED:
            return

        error_output = re.search(self.name + r': failed.*\n(.*)\n([\w\s/:]+\n)\n', output.strip())
        if not error_output:
            return

        self.signals = error_output.group(1).upper().split()
        lines: List[str] = error_output.group(2).split('\n')

        self.steps = []
        for line in lines:
            line = re.sub(r'E: (\w+) / F: (\w+)', r'\1/\2', line)
            self.steps.append(dict(zip(self.signals, line.strip().split())))


def parse_test_output(output: str) -> List[TestOutput]:
    result: List[TestOutput] = []
    for test_case in re.finditer(r'(\w+): (passed|failed)', output):
        test_name = test_case.group(1)
        status = TestStatus(test_case.group(2))

        result.append(TestOutput(test_name, status, output))

    return result


class Tests(DigitalModule):
    def __init__(self, cmd: List[str]):
        super().__init__(cmd)

    def run_test(self, schematic_path: Path, test_path: Path) -> List[TestOutput]:
        args = ["test", "-circ", str(schematic_path), "-tests", str(test_path), "-verbose"]

        result = super()._run(args)
        if result.returncode == 0:
            pass
        result_text = result.stdout.decode("utf-8").strip()
        return parse_test_output(result_text)
