import logging
import os
from collections import defaultdict
from pathlib import Path
import argparse
from typing import List, Dict, Tuple

import jinja2
import importlib.resources

from src.cse140l.digital.stats import GateStat, get_gate_count
from src.cse140l.digital.tests import TestOutput
from src.cse140l.digital.wrapper import Digital
from src.cse140l.gradescope.autograder_writer import AutograderWriter
from src.cse140l.gradescope.test_result import TestResult, TestStatus, TextFormat
from src.cse140l.lab.config import get_config_from_toml, LabConfig
from src.cse140l.log import log, setup_logger


def get_jinja_env() -> jinja2.Environment:
    templates_path = importlib.resources.files("cse140l.lab").joinpath("templates")
    loader = jinja2.FileSystemLoader(templates_path)
    return jinja2.Environment(loader=loader)


class LabRunner:
    def __init__(self, config_file: Path, gradescope_mode: bool = False, existing_tests: List[Path] = None):
        self.config: LabConfig = get_config_from_toml(config_file, gradescope_mode=gradescope_mode)
        self.submission_dir = self.config.submission_directory
        self.top_level = sorted(set(test.top_level for test in self.config.tests))
        self.autograder_writer = AutograderWriter(existing_tests=existing_tests)
        self.digital = Digital(self.config.digital_jar)
        self.env = get_jinja_env()
        self.generate_header()

    def create_header(self) -> str:
        missing_files = []
        found_files = []
        circuit_info = []
        analysis_errors = self.analyze_circuit()
        for top_level in self.top_level:
            if (schematic_path := self.get_schematic_path(top_level)).exists():
                found_files.append(top_level)
                circuit_info.append((top_level,
                    self.digital.svg.export_svg(schematic_path), analysis_errors[top_level] if analysis_errors is not None else None))
            else:
                missing_files.append(top_level)

        template = self.env.get_template("header.html.j2")

        output = template.render(
            {
                "circuit_info": circuit_info,
                "missing_files": missing_files,
                "lab_number": self.config.lab_number,
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

    def get_schematic_path(self, top_level: str) -> Path:
        return Path(self.submission_dir, f"{top_level}.dig")

    def analyze_circuit(self) -> Dict[str, List[str]] | None:
        if self.config.analyze is None:
            return None

        cached_circuits: Dict[str, List[GateStat]] = dict()
        analysis_failures: Dict[str, List[str]] = defaultdict(list)
        gate_info = lambda g: f"{gate_count}x {g.inputs}-input {g.bit_width} wide {g.name.upper()} gates" if g.inputs else f"{gate_count}x {g.bit_width} wide {g.name.upper()} gates"
        for analysis in self.config.analyze:
            for top_level in analysis.top_levels:
                if not self.get_schematic_path(top_level).exists():
                    analysis_failures[top_level].append(f"{top_level} not found!")
                    continue

                if top_level not in cached_circuits:
                    cached_circuits[top_level] = self.digital.stats.get_stats(self.get_schematic_path(top_level))

                for gate in analysis.gates:
                    gate_count = get_gate_count(cached_circuits[top_level], gate)
                    if gate.max_amount is not None and gate.max_amount < gate_count:
                        analysis_failures[top_level].append(f"greater than {gate_info(gate)}")

                    if gate.min_amount is not None and gate.min_amount > gate_count:
                        analysis_failures[top_level].append(f"less than {gate_info(gate)}")

        return analysis_failures


    def run_tests(self) -> None:
        for test in self.config.tests:
            dut: Path = self.get_schematic_path(test.top_level)
            outputs: List[TestOutput] = self.digital.test.run_test(dut, test.test_file)

            failed = []
            score = 0.
            status = TestStatus.FAILED
            error = False
            if outputs is not None and len(outputs) > 0:
                if outputs[0].error:
                    status = TestStatus.FAILED
                    score = 0
                    failed = []
                    error = True
                else:
                    failed: List[TestOutput] = list(filter(lambda t: t.outcome == TestStatus.FAILED, outputs))
                    score = (1. - (len(failed) / len(outputs))) * test.max_score
                    status = TestStatus.FAILED if len(failed) > 0 else TestStatus.PASSED


            result = {
                "name": test.name,
                "status": status,
                "score": score,
                "max_score": test.max_score,
                "visibility_on_success": test.visibility_on_success,
                "visibility_on_failure": test.visibility_on_failure,
            }

            log.debug(f"Testcase result: {result}")

            if error:
                result["output"] = outputs[0].output
                result["output_format"] = TextFormat.TEXT
            elif status == TestStatus.FAILED and len(failed) > 0:
                result["output"] = self.create_error_table(failed)
                result["output_format"] = TextFormat.HTML
            elif len(outputs) == 0:
                result["output"] = "We could not test your circuit. This could be due to misnamed ports or other circuit bugs."
                result["output_format"] = TextFormat.TEXT

            test_result: TestResult = TestResult(**result)
            self.autograder_writer.add_test(test_result)

    def generate_report(self, report_path: Path) -> None:
        self.autograder_writer.write_report(report_path)

    def report(self) -> None:
        self.autograder_writer.print_report()

def main():
    parser = argparse.ArgumentParser(description="Run the lab test benches as defined in the config file")

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

    parser.add_argument(
        "--gradescope",
        action="store_true",
        help="Gradescope autograder is enabled. (This sets some default values automatically)"
    )

    parser.add_argument(
        "-j",
        "--json_files",
        type=Path,
        nargs="+",
        help="Paths to pre-existing JSON files to merge into this one."
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode."
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Optional path to a file to write log output."
    )

    args = parser.parse_args()

    setup_logger(log_file=args.log_file, level=logging.INFO if not args.debug else logging.DEBUG)

    if not args.config_file.exists():
        log.error("Configuration file does not exist!")
        exit(1)

    os.chdir(args.config_file.absolute().parent)

    runner = LabRunner(args.config_file, gradescope_mode=args.gradescope, existing_tests=args.json_files)
    runner.run_tests()
    runner.generate_report(args.output_file)
    runner.report()

    runner.analyze_circuit()

if __name__ == '__main__':
    main()
