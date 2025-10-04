import logging
from pathlib import Path
from typing import List

import toml
from pydantic import BaseModel, PositiveFloat, field_validator, PositiveInt, NonNegativeInt, model_validator

from cse140l.gradescope.test_result import Visibility
from cse140l.log import log

class GateConfig(BaseModel):
    name: str
    inputs: PositiveInt | None = None
    bit_width: PositiveInt | None = 1
    max_amount: NonNegativeInt | None = None
    min_amount: NonNegativeInt | None = None

class AnalyzeConfig(BaseModel):
    top_levels: List[str]
    gates: List[GateConfig]

class TestConfig(BaseModel):
    name: str
    max_score: PositiveFloat
    test_file: Path
    top_level: str
    visibility_on_success: str | Visibility
    visibility_on_failure: str | Visibility

    @field_validator("visibility_on_success", "visibility_on_failure")
    @classmethod
    def validate_visibility(cls, value: str):
        if value not in Visibility.__members__.values():
            raise ValueError(f"Invalid visibility: {value}")
        return Visibility(value)


class LabConfig(BaseModel):
    digital_jar: Path
    lab_number: PositiveInt
    submission_directory: Path | None
    tests: List[TestConfig]
    analyze: List[AnalyzeConfig] | None = None

    @field_validator("submission_directory")
    @classmethod
    def validate_directory(cls, value: Path):
        if not value.exists():
            raise ValueError(f"Directory does not exist: {value}")
        return value

    @model_validator(mode='after')
    def validate_test_files(self):
        for test in self.tests:
            if not test.test_file.exists():
                # Critical, TA staff forgot to submit a file
                raise ValueError(f"Test file does not exist: {test.test_file}")

            top_level = Path(self.submission_directory, f"{test.top_level}.dig")
            if not top_level.exists():
                # Non-critical, student chose not to submit to the file, but we need to grade the other parts.
                log.error(f"Top level does not exist: {top_level}")
                continue
        return self

def get_config_from_toml(config_file: Path, submission_dir: Path = None, gradescope_mode: bool = False) -> LabConfig:
    raw_config = toml.load(config_file)

    if gradescope_mode:
        raw_config["digital_jar"] = Path("/usr/local/bin/Digital.jar")
        raw_config["submission_directory"] = Path("/autograder/submission")

    if submission_dir is not None:
        raw_config["submission_directory"] = submission_dir

    return LabConfig(**raw_config)