from typing import List
from pathlib import Path
from cse140l.digital.util import DigitalModule


class SVGExport(DigitalModule):
    def __init__(self, cmd: List[str]):
        super().__init__(cmd)

    def export_svg(self, schematic_path: Path, svg_path: Path = None) -> str:
        args = ["svg", "-ieee", "-dig", str(schematic_path)]

        if svg_path is not None:
            args += ["-svg", str(svg_path)]

        result = super()._run(args)
        return result.stdout.decode("utf-8")