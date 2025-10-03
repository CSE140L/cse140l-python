import argparse
import os
from typing import Dict

import questionary
import csv
import yaml
from pathlib import Path

from src.cse140l.digital.wrapper import Digital
from src.cse140l.lab.config import get_config_from_toml


class ManualGrader:
    def __init__(self, config_file: Path, exported_submissions: Path, jar_file: Path = None) -> None:
        self.config = get_config_from_toml(config_file.absolute())
        if jar_file:
            self.config.digital_jar = jar_file.absolute()
        self.digital: Digital = Digital(jar_file)
        self.exported_submissions: Path = exported_submissions.absolute()
        self._generate_metadata()

    def _generate_metadata(self) -> None:
        submission_metadata_file = Path(self.exported_submissions, "submission_metadata.yml")
        with open(submission_metadata_file, "r") as f:
            submission_metadata: Dict = yaml.safe_load(f.read())

        self.meta_data: Dict[str, Dict] = {}
        for submission in submission_metadata.keys():
            pass
            # self.meta_data[submission["submi["name"]] = "Hello"

        print(self.meta_data)

    def menu(self) -> None:
        questionary.select("What do you want to do?", choices=["Grade", "Test"]).ask()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manually review submissions and adjust grades if necessary")

    parser.add_argument(
        "config_file",
        type=Path,
        help="Path to the lab's config file"
    )
    parser.add_argument(
        "submissions_dir",
        type=Path,
        help="Path to gradescope exported submissions"
    )
    parser.add_argument(
        "-j",
        "--digital-jar-file",
        type=Path,
        help="Path to the digital jar file in case you want to overwrite it"
    )

    args = parser.parse_args()

    grader = ManualGrader(args.config_file, args.submissions_dir, args.digital_jar_file)

    # grader.menu()