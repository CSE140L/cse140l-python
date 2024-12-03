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

        error_output = re.search(re.escape(self.name) + r': failed.*\n(.*)\n([\w\s/:]+\n)\n', self.output.strip())
        if not error_output:
            return

        self.signals = error_output.group(1).upper().split()
        lines: List[str] = error_output.group(2).split('\n')

        self.steps = []
        for line in lines:
            line = re.sub(r'E: (\w+) / F: (\w+)', r'\1/\2', line)
            self.steps.append(dict(zip(self.signals, line.strip().split())))

    def __repr__(self):
        return self.name


def parse_test_output(output: str) -> List[TestOutput]:
    result: List[TestOutput] = []
    print(output)
    # https://regex101.com/r/33A4b9/1
    for test_case in re.finditer(r'^(?![\d\s]*E:.*)(.+): ([\w ]+)', output, re.MULTILINE):
        test_name = test_case.group(1)
        raw_status = test_case.group(2)
        if raw_status.lower() == "passed":
            status = TestStatus.PASSED
        elif raw_status.lower() == "failed":
            status = TestStatus.FAILED
        else:
            status = "error"
        logger.debug(f'{test_name}: {status}')
        error = status == "error"
        result.append(TestOutput(test_name, status, raw_status if error else output, error))

    return result

def get_num_tests_from_output(output: str) -> int:
   return len(re.findall(r'(\w+):', output))


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
                f"STDOUT: {result.stdout.decode('utf-8')}\nSTDERR: {result.stderr.decode('utf-8')}\nERR:{result.returncode}",
                True
            )
            logger.debug(f"Error running {test_path}")
            return [error_result]
        result_text = result.stdout.decode("utf-8").strip()
        return parse_test_output(result_text)

if __name__ == '__main__':
    output = """
test_1: Test signal BEGIN not found in the circuit!
test_2: passed
test_3: Component STUFF not found!
test_4: failed
tests have failed
    
0 0 0 0 E: 1 / F: 2 0 0 0
    """
    print(get_num_tests_from_output(output))

    # REGEX = r'^(\w+): ((\w+)[\n ][\w ]*)\n'
    REGEX = r'^(\w+): (\w+)[\n ]([\w !]*)'

    print(re.findall(REGEX, output, flags=re.MULTILINE))

    new_output = """
test_1234+2341: failed (100%)
OPERAND_ONE OPERAND_TWO ERROR_FLAGS SUM
0x1234 0x2341 E: 7 / F: 0 3BDB

test_1500+2000: failed (100%)
OPERAND_ONE OPERAND_TWO ERROR_FLAGS SUM
0x1500 0x2000 E: 4 / F: 0 3B00

test_2045+3040: failed (100%)
OPERAND_ONE OPERAND_TWO ERROR_FLAGS SUM
204B 0x3040 E: A / F: 0 B0EB

test_3210+0423: failed (100%)
OPERAND_ONE OPERAND_TWO ERROR_FLAGS SUM
0x3210 0x423 E: 4 / F: 0 3C33

test_5946+3461: passed
test_999+1111: passed
test_2879+1090: passed
"""