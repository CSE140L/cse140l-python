# Project: CSE 140L Report Viewer

## General Instructions:

- When writing new Python 3.12 code, please follow the existing code style.
- Ensure all new functions and classes have Python comments.
- Prefer object oriented programming paradigms where appropriate (such as data structures)
- All Python code should be typed correctly
- None values should be checked before using them.
- Use a global log tool instead of print statements
- All code should be compatible with Python 3.12 plus dependencies.
- All code should be modularized.

## Coding Style:

- Use 4 spaces for indentation.
- Segment import statements by including Python builtin libraries first, then external libraries, then any local libraries.
- Sort the import statements by line length
- Prefer snake case for all naming except for classes which should be CamelCase. Global constant values should be capitalized.
- Prefer list comprehension and dictionary comprehension where possible.
- Private class members should be prefixed with an underscore (`_`).

## Specific Script: `./src/cse140l/lab/runner.py`

- This file contains the CSE 140L autograding main function, and is what is run when we want to autograde

## Specific Script: `./src/report_server/report_server.py`

- This file contains the main function for the report server, which provides an HTML report of the student's score when they access a specific search path

## Testing Functionality

- To test the main CSE 140L autograding system, please run `make -C ./tests`

## Regarding Dependencies:

- Avoid introducing new external dependencies unless absolutely necessary.
- If a new dependency is required, please state the reason.
- Use `uv add` to install the dependency, do not use pip.
