from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class ReferenceNote:
    start_s: float
    duration_s: float
    midi: float

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


class Melody:
    def __init__(self, notes: List[ReferenceNote]):
        self.notes = sorted(notes, key=lambda n: n.start_s)

    @classmethod
    def from_csv(cls, path: Path) -> "Melody":
        notes: List[ReferenceNote] = []
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                start_s = float(row["start_s"])
                duration_s = float(row["duration_s"])
                midi = float(row["midi"])
                notes.append(ReferenceNote(start_s, duration_s, midi))
        return cls(notes)
