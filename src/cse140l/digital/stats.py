import csv

from io import StringIO
from typing import List, overload
from pathlib import Path

from pydantic import PositiveInt, BaseModel

from cse140l.digital.util import DigitalModule
from cse140l.lab.config import GateConfig


class GateStat(BaseModel):
    name: str
    count: PositiveInt
    inputs: PositiveInt | None = None
    bit_width: PositiveInt | None = None
    addr_bit_width: PositiveInt | None = None

    def __eq__(self, other: GateConfig):
        if isinstance(other, GateConfig):
            return self.name == other.name.upper() and self.inputs == other.inputs and self.bit_width == other.bit_width
        else:
            return super().__eq__(other)



class CircuitStats(DigitalModule):
    def __init__(self, cmd: List[str]):
        super().__init__(cmd)

    def get_stats(self, schematic_path: Path, csv_path: Path = None) -> List[GateStat]:
        args = ["stats", "-dig", str(schematic_path)]

        if csv_path is not None:
            args += ["-svg", str(csv_path)]

        result = super()._run(args)

        if result.returncode != 0:
            return []
            # raise RuntimeError(result.stderr.decode("utf-8"))

        csv_reader = csv.reader(StringIO(result.stdout.decode("utf-8")))
        _ = next(csv_reader)

        result_list: List[GateStat] = []
        for row in csv_reader:
            gate_dict = {
                "name": row[0].upper(),
                "count": PositiveInt(row[4].strip()),
            }

            if inputs := row[1].strip():
                gate_dict["inputs"] = PositiveInt(inputs)

            if bit_width := row[2].strip():
                gate_dict["bit_width"] = PositiveInt(bit_width)

            if addr_bit_width := row[3].strip():
                gate_dict["addr_bit_width"] = PositiveInt(addr_bit_width)

            gate: GateStat = GateStat.model_validate(gate_dict)
            result_list.append(gate)

        return result_list

def get_gate_count(gate_list: List[GateStat], gate_config: GateConfig) -> int:
    for gate in gate_list:
        if gate == gate_config:
            return gate.count
    return 0
