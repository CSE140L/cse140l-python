import re
from typing import List
from pathlib import Path
from cse140l.digital.util import DigitalModule
from cse140l.gradescope.test_result import TestStatus

import logging

logger = logging.getLogger(__name__)

class TestOutput:
    def __init__(self, name: str, outcome: TestStatus, output: str, err: bool):
        self.name = name
        self.outcome = outcome
        self.error = err
        self.output = output
        self.signals: List[str] = []
        self.steps: List[dict] = []

        if not self.error:
            self._generate_table()

    def _generate_table(self) -> None:
        if self.outcome != TestStatus.FAILED and not self.error:
            return

        error_output = re.search(self.name + r': failed.*\n(.*)\n([\w\s/:]+\n)\n', self.output.strip())
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
        logger.debug(f'{test_name}: {status}')
        result.append(TestOutput(test_name, status, output, False))

    return result


class Tests(DigitalModule):
    def __init__(self, cmd: List[str]):
        super().__init__(cmd)

    def run_test(self, schematic_path: Path, test_path: Path) -> List[TestOutput]:
        if not test_path.exists():
            return [TestOutput(
                f"{test_path} not found!",
                TestStatus.FAILED,
                "",
                True
            )]

        if not schematic_path.exists():
            return [TestOutput(
                f"{schematic_path} not found!",
                TestStatus.FAILED,
                "",
                True
            )]

        args = ["test", "-circ", str(schematic_path), "-tests", str(test_path), "-verbose"]

        result = super()._run(args)

        # Digital by default returns error codes > 100 for things like file not found etc.
        if result.returncode > 100:
            error_result = TestOutput(
                f"{test_path}",
                TestStatus.FAILED,
                f"STDOUT: {result.stdout.decode('utf-8')}\nSTDERR: {result.stderr.decode('utf-8')}",
                True
            )
            logger.debug(f"Error running {test_path}")
            return [error_result]

        result_text = result.stdout.decode("utf-8").strip()
        return parse_test_output(result_text)
