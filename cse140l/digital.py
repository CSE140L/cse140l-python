import subprocess
from pathlib import Path
from typing import List, Tuple
import json
import argparse

class Digital:
    def __init__(self, jar_file: Path) -> None:
        self.jar_file = jar_file
        self.cmd = ["java", "-cp", str(self.jar_file), "CLI"]

    def _run(self, command: List[str]) -> subprocess.CompletedProcess:
        process = subprocess.run(self.cmd + command, capture_output=True)
        return process

    def export_schematic(self, schematic_path: Path, verilog_path: Path) -> subprocess.CompletedProcess:
        args = ["verilog", "-dig", str(schematic_path), "-verilog", str(verilog_path)]
        result = self._run(args)
        return result

    def export_schematics(self, schematic_dir: Path, verilog_dir: Path, top_level: Path = None,
                          gradescope_results: Path = None) -> List[Tuple[Path, subprocess.CompletedProcess]]:

        def get_verilog_path(circuit: Path) -> Path:
            return Path(verilog_dir, circuit.stem + ".v")

        if not schematic_dir.is_dir():
            raise FileNotFoundError

        verilog_dir.mkdir(parents=True, exist_ok=True)

        if top_level is not None:
            with open(top_level, 'r') as f:
                modules = [line.rstrip('\n') for line in f]
            schematics_to_export = [
                    schematic for schematic in schematic_dir.iterdir() if schematic.is_file() and schematic.stem in modules
            ]
        else:
            schematics_to_export = [schematic for schematic in schematic.iterdir() if schematic.is_file()]

        schematics_to_export = list(filter(lambda p: str(p).endswith(".dig"), schematics_to_export))

        exported_results = [(schematic_path, self.export_schematic(schematic_path, get_verilog_path(schematic_path)))
                            for schematic_path in schematics_to_export]

        if gradescope_results is not None:
            outputs = []
            status = "passed"
            for schematic, result in exported_results:
                line = f"`{schematic}`: "
                if result.returncode != 0:
                    status = "failed"
                line += status.capitalize()
                outputs.append(line)

            res = {
                "tests": [
                    {
                        "name": "Exporting Schematics to Verilog",
                        "score": "0",
                        "max_score": "0",
                        "output": "\n\n".join(outputs),
                        "output_format": "md",
                        "status": status
                    }
                ]
            }

            with open(gradescope_results, "w") as gradescope_results_file:
                json.dump(res, gradescope_results_file, indent=4)

        return exported_results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--jar_file", required=True, type=Path)
    parser.add_argument(
        "-s", "--schematics_dir",
        type=Path,
        help="Directory containing schematics."
    )
    parser.add_argument(
        "-t", "--top_level",
        type=Path,
        required=False,
        help="Path containing the top level schematics to export in the schematics_dir"
    )
    parser.add_argument(
        "-v", "--verilog_dir",
        type=Path,
        help="Directory containing schematics."
    )
    parser.add_argument("-g", "--gradescope_results", default=None, type=Path, help="File to save results for Gradescope to")

    args = parser.parse_args()

    digital = Digital(args.jar_file)

    digital.export_schematics(args.schematics_dir, args.verilog_dir, top_level=args.top_level, gradescope_results=args.gradescope_results)
