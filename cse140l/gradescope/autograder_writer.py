from typing import List
from cse140l.gradescope.test_result import TestResult, TextFormat
from json import dumps
from pathlib import Path

class AutograderWriter:
    def __init__(self, output: str = None, output_format: TextFormat = TextFormat.TEXT):
        self.test_results: List[TestResult] = []
        self.output: str = output
        self.output_format: TextFormat = output_format

    def set_output(self, output: str, output_format: TextFormat = TextFormat.TEXT):
        self.output = output
        self.output_format = output_format

    def add_test(self, test_result: TestResult):
        self.test_results.append(test_result)

    def write_report(self, filename: Path | str) -> None:
        with open(filename, 'w') as f:
            f.write(str(self))

    def __str__(self) -> str:
        report: dict = {
            "tests": [res.to_dict() for res in self.test_results]
        }

        if self.output is not None:
            report["output"] = self.output
            report["output_format"] = self.output_format

        return dumps(report)


if __name__ == '__main__':
    from test_result import TestStatus

    writer = AutograderWriter()
    test = TestResult(name="Hello World!", score=0, max_score=10, status=TestStatus.PASSED)
    writer.add_test(test)
    print(writer)
    writer.write_report(Path("report.json"))