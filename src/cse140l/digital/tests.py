import re
from typing import List
from pathlib import Path
import xml.etree.ElementTree as et
import io
from typing import Optional

from cse140l.digital.util import DigitalModule
from cse140l.gradescope.test_result import TestStatus
from cse140l.log import log, is_logging_to_file

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


def parse_test_output(output: str, testcase_names: List[str]) -> List[TestOutput]:
    result: List[TestOutput] = []
    if is_logging_to_file():
        log.info(f"Test Output:\n{output}")
    for t in testcase_names:
        test_case = re.search(rf'({t}): (.*)', output)
        if not test_case:
            log.warning(f"Could not find test case '{t}' in output.")
            continue
        test_name = test_case.group(1)
        raw_status = test_case.group(2)
        raw_status_lower = raw_status.lower().strip()
        if raw_status_lower == "passed":
            status = TestStatus.PASSED
        elif "failed" in raw_status_lower:
            status = TestStatus.FAILED
        else:
            status = "error"
            log.error(f"Error running testcase '{test_name}' (reason: {raw_status.strip()})")
        error = status == "error"
        test_output = TestOutput(test_name, status, raw_status if error else output, error)
        result.append(test_output)

    if len(result) == 0:
        log.error("No test cases found!")

    return result

def get_num_tests_from_output(output: str) -> int:
   return len(re.findall(r'(\w+):', output))

def extract_all_testcase_labels(xml_path: Path) -> List[str]:
    """
    Reads an XML file and extracts the label string for all <visualElement>
    nodes where <elementName> is "Testcase".
    """
    labels = []

    try:
        root = et.parse(xml_path).getroot()
    except Exception as e:
        log.error(f"Error reading or parsing file: {e}")
        return labels

    # Iterate over all <visualElement> tags
    for element in root.findall('.//visualElement'):
        # 1. Filter: Check if <elementName> is "Testcase"
        element_name_tag = element.find('elementName')
        if element_name_tag is None or element_name_tag.text != 'Testcase':
            continue

        # 2. Extract: Look for the corresponding "Label" entry
        attributes = element.find('elementAttributes')
        if attributes is None:
            continue

        for entry in attributes.findall('entry'):
            children = list(entry)

            # Check if the first child is <string>Label</string>
            if (len(children) >= 1 and
                    children[0].tag == 'string' and
                    children[0].text == 'Label'):

                # The desired value is the text of the second child <string> element.
                if len(children) > 1 and children[1].tag == 'string':
                    labels.append(children[1].text)

                # Once the label entry is found for this Testcase, we can stop
                # looking at other entries for this element and move to the next visualElement.
                break

    return labels

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
            log.debug(f"Error running {test_path}")
            return [error_result]

        result_text = result.stdout.decode("utf-8").strip()
        return parse_test_output(result_text, extract_all_testcase_labels(test_path))
