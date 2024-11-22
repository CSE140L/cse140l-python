from pathlib import Path
from typing import List

import toml
from pydantic import BaseModel, PositiveFloat, field_validator, PositiveInt

from cse140l.gradescope.test_result import Visibility


class TestConfig(BaseModel):
    name: str
    max_score: PositiveFloat
    test_file: Path
    top_level: str
    visibility_on_success: str
    visibility_on_failure: str

    @field_validator("visibility_on_success", "visibility_on_failure")
    @classmethod
    def validate_visibility(cls, value):
        if value not in Visibility.__members__.values():
            raise ValueError(f"Invalid visibility: {value}")
        return value


class LabConfig(BaseModel):
    digital_jar: Path
    lab_number: PositiveInt
    submission_directory: Path
    tests: List[TestConfig]

def validate_config(config_file: Path) -> dict:
    config = toml.load(config_file)
    LabConfig.model_validate(config)

    return config