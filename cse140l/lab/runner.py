import os
from pathlib import Path
import argparse
from typing import List

import jinja2
import importlib.resources

from cse140l.digital.tests import TestOutput
from cse140l.digital.wrapper import Digital
from cse140l.gradescope.autograder_writer import AutograderWriter
from cse140l.gradescope.test_result import TestResult, TestStatus, TextFormat
from cse140l.lab.config import validate_config


def get_jinja_env() -> jinja2.Environment:
    templates_path = importlib.resources.files("cse140l.lab").joinpath("templates")
    loader = jinja2.FileSystemLoader(templates_path)
    return jinja2.Environment(loader=loader)


class LabRunner:
    def __init__(self, config_file: Path):
        self.config = validate_config(config_file)
        self.submission_dir = self.config["submission_directory"]
        self.top_level = sorted(set(test["top_level"] for test in self.config["tests"]))
        self.autograder_writer = AutograderWriter()
        self.digital = Digital(self.config["digital_jar"])
        self.env = get_jinja_env()
        self.generate_header()

    def create_header(self) -> str:
        missing_files = []
        found_files = []
        circuit_svgs = []
        for top_level in self.top_level:
            if Path(self.submission_dir, f"{top_level}.dig").exists():
                found_files.append(top_level)
                circuit_svgs.append((top_level,
                    self.digital.svg.export_svg(Path(self.submission_dir, f"{top_level}.dig"))))
            else:
                missing_files.append(top_level)

        template = self.env.get_template("header.html.j2")

        output = template.render(
            {
                "circuit_svgs": circuit_svgs,
                "missing_files": missing_files,
                "lab_number": self.config["lab_number"],
            }
        )

        return output

    def create_error_table(self, failed_tests: List[TestOutput]) -> str:
        template = self.env.get_template("error_table.html.j2")

        output = template.render(
            {
                "failed_tests": failed_tests,
            }
        )

        return output

    def generate_header(self) -> None:
        self.autograder_writer.set_output(self.create_header(), TextFormat.HTML)

    def run_tests(self) -> None:
        for test in self.config["tests"]:
            dut: Path = Path(self.submission_dir, f"{test['top_level']}.dig")
            outputs: List[TestOutput] = self.digital.test.run_test(dut, test["test_file"])
            failed: List[TestOutput] = list(filter(lambda t: t.outcome == TestStatus.FAILED, outputs))
            score = (1. - (len(failed) / len(outputs))) * test["max_score"]
            status = TestStatus.FAILED if len(failed) > 0 else TestStatus.PASSED

            result = {
                "name": test["name"],
                "status": status,
                "score": score,
                "max_score": test["max_score"],
                "visibility_on_success": test["visibility_on_success"],
                "visibility_on_failure": test["visibility_on_failure"],
            }

            if status == TestStatus.FAILED:
                result["output"] = self.create_error_table(failed)
                result["output_format"] = TextFormat.HTML


            test_result: TestResult = TestResult(**result)
            self.autograder_writer.add_test(test_result)

    def report(self, report_path: Path) -> None:
        self.autograder_writer.write_report(report_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert a TOML configuration file to a JSON file.")

    parser.add_argument(
        "config_file",
        type=Path,
        help="Path to the input TOML configuration file."
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Path to the output the report JSON file."
    )
    args = parser.parse_args()

    if not args.config_file.exists():
        print("Configuration file does not exist.")
        exit(1)

    os.chdir(args.config_file.absolute().parent)

    runner = LabRunner(args.config_file)
    runner.run_tests()
    runner.report(args.output_file)
