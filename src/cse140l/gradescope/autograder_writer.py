from typing import List
from src.cse140l.gradescope.test_result import TestResult, TextFormat
from json import dumps, load
from pathlib import Path
from minify_html import minify

class AutograderWriter:
    def __init__(self, existing_tests: List[Path] = None):
        self.test_results: List[TestResult] = []
        if existing_tests:
            for test_file in existing_tests:
                with open(test_file, 'r') as f:
                    test_json = load(f)
                for t in test_json["tests"]:
                    self.test_results.append(TestResult(**t))
        self.output: str | None = None
        self.output_format: TextFormat = TextFormat.TEXT

    def set_output(self, output: str, output_format: TextFormat = TextFormat.TEXT):
        self.output = output
        self.output_format = output_format
        if self.output_format == TextFormat.HTML or self.output_format == TextFormat.SIMPLE_FORMAT:
            self.output = minify(self.output)


    def add_test(self, test_result: TestResult):
        self.test_results.append(test_result)

    def write_report(self, filename: Path | str) -> None:
        with open(filename, 'w') as f:
            f.write(str(self))

    def print_report(self) -> None:
        for test_result in self.test_results:
            print(f"{test_result.name}: {test_result.status.capitalize()} ({test_result.score}/{test_result.max_score})")

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
