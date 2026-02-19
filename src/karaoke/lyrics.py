from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class LyricLine:
    time_s: float
    text: str


class Lyrics:
    def __init__(self, lines: List[LyricLine]):
        self.lines = sorted(lines, key=lambda x: x.time_s)

    @classmethod
    def from_lrc(cls, path: Path) -> "Lyrics":
        lines: List[LyricLine] = []
        timestamp_re = re.compile(r"\\[(\\d+):(\\d+(?:\\.\\d+)?)\\]")
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            stamps = timestamp_re.findall(raw)
            if not stamps:
                continue
            text = timestamp_re.sub("", raw).strip()
            for mm, ss in stamps:
                time_s = int(mm) * 60 + float(ss)
                lines.append(LyricLine(time_s=time_s, text=text))
        return cls(lines)

    def current_and_next(self, time_s: float) -> Tuple[Optional[LyricLine], Optional[LyricLine]]:
        if not self.lines:
            return None, None
        idx = 0
        while idx + 1 < len(self.lines) and self.lines[idx + 1].time_s <= time_s:
            idx += 1
        current = self.lines[idx] if self.lines[idx].time_s <= time_s else None
        next_line = self.lines[idx + 1] if idx + 1 < len(self.lines) else None
        return current, next_line
