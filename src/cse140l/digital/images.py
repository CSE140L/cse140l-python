from typing import List
from pathlib import Path
import cairosvg
import base64
from io import BytesIO
from cse140l.digital.util import DigitalModule


class ImageExport(DigitalModule):
    def __init__(self, cmd: List[str]):
        super().__init__(cmd)

    def export_svg(self, schematic_path: Path, svg_path: Path = None) -> str:
        args = ["svg", "-ieee", "-dig", str(schematic_path)]

        if svg_path is not None:
            args += ["-svg", str(svg_path)]

        result = super()._run(args)
        return result.stdout.decode("utf-8")

    def export_png_as_base64(self, schematic_path: Path) -> str:
        png_output = BytesIO()
        svg_str = self.export_svg(schematic_path, None)

        cairosvg.svg2png(
            bytestring=svg_str.encode('utf-8'),
            write_to=png_output
        )

        png_binary_data = png_output.getvalue()

        base64_encoded_data = base64.b64encode(png_binary_data).decode('utf-8')

        return f"data:image/png;base64,{base64_encoded_data}"