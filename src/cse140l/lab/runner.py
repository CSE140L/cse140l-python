import logging
import os
from collections import defaultdict
from pathlib import Path
import argparse
from typing import List, Dict, Tuple
import base64

import requests
import json

from cse140l.digital.stats import GateStat, get_gate_count
from cse140l.digital.tests import TestOutput
from cse140l.digital.wrapper import Digital
from cse140l.gradescope.autograder_writer import AutograderWriter
from cse140l.gradescope.test_result import TestResult, TestStatus, TextFormat
from cse140l.lab.config import get_config_from_toml, LabConfig
from cse140l.log import log, setup_logger





class LabRunner:
    def __init__(self, config_file: Path, gradescope_mode: bool = False, existing_tests: List[Path] = None, report_server_url: str = None, student_id: str = None):
        self.config: LabConfig = get_config_from_toml(config_file, gradescope_mode=gradescope_mode)
        self.submission_dir = self.config.submission_directory
        self.top_level = sorted(set(test.top_level for test in self.config.tests))
        self.autograder_writer = AutograderWriter(existing_tests=existing_tests)
        self.digital = Digital(self.config.digital_jar)
        self.report_server_url = report_server_url
        self.student_id = student_id
        self.all_failed_tests = []
        self.circuit_info = []
        self.missing_files = []
        self.test_errors = defaultdict(list)

    def _test_output_to_dict(self, test_output: TestOutput) -> Dict:
        """Converts a TestOutput object to a serializable dictionary."""
        return {
            "name": test_output.name,
            "outcome": test_output.outcome,
            "output": test_output.output,
            "error": test_output.error,
            "signals": test_output.signals,
            "steps": test_output.steps,
        }

    def prepare_report_data(self) -> Dict:
        """Gathers all data needed for the HTML report."""
        analysis_errors = self.analyze_circuit()

        all_errors = defaultdict(list)
        if analysis_errors:
            for top_level, errors in analysis_errors.items():
                all_errors[top_level].extend(errors)

        for top_level, errors in self.test_errors.items():
            all_errors[top_level].extend(errors)

        for top_level in self.top_level:
            schematic_path = self.get_schematic_path(top_level)
            if schematic_path.exists():
                self.circuit_info.append({
                    "top_level": top_level,
                    "base64_png_data": "data:image/svg+xml;base64," + base64.b64encode(
                        self.digital.img.export_svg(schematic_path).encode("utf-8")).decode("ascii"),
                    "analysis_errors": all_errors.get(top_level)
                })
            else:
                self.missing_files.append(top_level)

        serializable_failed_tests = [
            {
                "test_name": test["test_name"],
                "failed_steps": [self._test_output_to_dict(step) for step in test["failed_steps"]]
            } for test in self.all_failed_tests
        ]

        return {
            "lab_number": self.config.lab_number,
            "circuit_info": self.circuit_info,
            "missing_files": self.missing_files,
            "all_failed_tests": serializable_failed_tests,
        }

    def post_report(self, url: str, student_id: str, token: str) -> None:
        """Posts the report data to the report server."""
        if not url or not student_id or not token:
            log.warning("Report server URL, student ID, or token not provided. Skipping report submission.")
            return

        report_data = self.prepare_report_data()
        endpoint = f"{url.rstrip('/')}/report/{self.config.lab_number}/{student_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(endpoint, headers=headers, data=json.dumps(report_data))
            response.raise_for_status()
            log.info(f"Successfully posted report for student {student_id} to {endpoint}")
            log.info(f"View report at {endpoint}")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to post report to server: {e}")
            if e.response is not None:
                log.error(f"Response status: {e.response.status_code}")
                log.error(f"Response body:\n{e.response.text}")
            else:
                log.error("No response from server.")

    def get_schematic_path(self, top_level: str) -> Path:
        return Path(self.submission_dir, f"{top_level}.dig")

    def analyze_circuit(self) -> Dict[str, List[str]] | None:
        if self.config.analyze is None:
            return None

        cached_circuits: Dict[str, List[GateStat]] = dict()
        analysis_failures: Dict[str, List[str]] = defaultdict(list)
        gate_info = lambda g: f"{gate_count}x {g.inputs}-input {g.bit_width}-wide {g.name.upper()} gates" if g.inputs else f"{gate_count}x {g.bit_width} wide {g.name.upper()} gates"
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
                        analysis_failures[top_level].append(f"Circuit has {gate_info(gate)} (Maximum of {gate.max_amount} allowed for this lab)")

                    if gate.min_amount is not None and gate.min_amount > gate_count:
                        analysis_failures[top_level].append(f"Circuit has {gate_info(gate)} (Minimum of {gate.min_amount} allowed for this lab)")

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
                    error_message = outputs[0].output if outputs[0].output else outputs[0].name
                    self.test_errors[test.top_level].append(f"Error running test '{test.name}': {error_message}")
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
                self.all_failed_tests.append({"test_name": test.name, "failed_steps": failed})
                output_text = f"{len(failed)} out of {len(outputs)} test vectors failed."
                if self.report_server_url and self.student_id:
                    fragment = test.name.lower().replace(' ', '-')
                    report_url = f"{self.report_server_url.rstrip('/')}/report/{self.config.lab_number}/{self.student_id}#{fragment}"
                    output_text += f" See [web report]({report_url}) for details."
                    result["output_format"] = TextFormat.MARKDOWN
                else:
                    output_text += " See web report for details."
                    result["output_format"] = TextFormat.TEXT
                result["output"] = output_text
            elif len(outputs) == 0:
                result["output"] = "We could not test your circuit. This could be due to misnamed ports or other circuit bugs."
                result["output_format"] = TextFormat.TEXT

            test_result: TestResult = TestResult(**result)
            self.autograder_writer.add_test(test_result)

    def generate_report(self, report_path: Path) -> None:
        if self.report_server_url and self.student_id:
            report_url = f"{self.report_server_url.rstrip('/')}/report/{self.config.lab_number}/{self.student_id}"
            output_text = f"Your detailed web report is available at [{report_url}]({report_url})."
            self.autograder_writer.set_output(output_text, output_format=TextFormat.MARKDOWN)
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
        "--log_file",
        type=str,
        default=None,
        help="Optional path to a file to write log output."
    )

    parser.add_argument(
        "--report-server-url",
        type=str,
        default=os.environ.get("REPORT_SERVER_URL"),
        help="URL of the report server. Can also be set with REPORT_SERVER_URL environment variable."
    )

    parser.add_argument(
        "--student-id",
        type=str,
        default=os.environ.get("STUDENT_ID"),
        help="Student ID. Can also be set with STUDENT_ID environment variable."
    )

    parser.add_argument(
        "--auth-token",
        type=str,
        default=os.environ.get("REPORT_SERVER_AUTH_TOKEN"),
        help="Authentication token for the report server. Can also be set with REPORT_SERVER_AUTH_TOKEN environment variable."
    )

    args = parser.parse_args()

    setup_logger(log_file=args.log_file, level=logging.INFO if not args.debug else logging.DEBUG)

    if not args.config_file.exists():
        log.error("Configuration file does not exist!")
        exit(1)

    os.chdir(args.config_file.absolute().parent)

    runner = LabRunner(
        args.config_file,
        gradescope_mode=args.gradescope,
        existing_tests=args.json_files,
        report_server_url=args.report_server_url,
        student_id=args.student_id
    )
    runner.run_tests()
    runner.generate_report(args.output_file)
    runner.report()
    
    runner.post_report(args.report_server_url, args.student_id, args.auth_token)

if __name__ == '__main__':
    main()
