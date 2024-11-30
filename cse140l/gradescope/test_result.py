from dataclasses import dataclass
from enum import StrEnum
from typing import List
from json import dumps

from minify_html import minify


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class Visibility(StrEnum):
    HIDDEN = "hidden"
    AFTER_DUE = "after_due_date"
    AFTER_PUBLISHED = "after_published"
    VISIBLE = "visible"


class TextFormat(StrEnum):
    TEXT = "text"
    HTML = "html"
    SIMPLE_FORMAT = "simple_format"  # Should this be the default for HTML output?
    MARKDOWN = "md"
    ANSI = "ansi"


@dataclass
class TestResult:
    name: str
    score: float
    max_score: float
    status: TestStatus
    visibility: Visibility = None
    visibility_on_success: Visibility = Visibility.HIDDEN
    visibility_on_failure: Visibility = Visibility.HIDDEN
    number: str = None
    output: str = None
    tags: List[str] = None
    name_format: TextFormat = TextFormat.TEXT
    output_format: TextFormat = TextFormat.TEXT

    def __str__(self) -> str:
        return f"Testcase {self.name}: {self.score:.2f}/{self.max_score:.2f}"

    def to_dict(self) -> dict:
        result: dict = {
            "score": self.score,
            "max_score": self.max_score,
            "status": self.status,
            "name": self.name,
            "name_format": self.name_format
        }

        if self.visibility:
            result["visibility"] = self.visibility
        else:
            if self.status == TestStatus.PASSED:
                result["visibility"] = self.visibility_on_success
            else:
                result["visibility"] = self.visibility_on_failure

        if self.number:
            result["number"] = self.number

        if self.output:
            result["output_format"] = self.output_format
            if self.output_format == TextFormat.HTML or self.output_format == TextFormat.SIMPLE_FORMAT:
                result["output"] = minify(self.output)

        if self.tags:
            result["tags"] = self.tags


        return result

    def to_json(self) -> str:
        return dumps(self.to_dict())