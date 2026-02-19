from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .config import NoteTrackingConfig
from .dsp import hz_to_midi, rms


@dataclass
class UserNote:
    start_s: float
    end_s: float
    midi: float

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


@dataclass
class _ActiveNote:
    start_s: float
    last_voiced_s: float
    midi_values: List[float] = field(default_factory=list)


class NoteTracker:
    def __init__(self, config: NoteTrackingConfig):
        self.config = config
        self.noise_floor = 0.0
        self.active: Optional[_ActiveNote] = None

    def process(self, time_s: float, frame: np.ndarray, pitch_hz: Optional[float]) -> List[UserNote]:
        notes: List[UserNote] = []
        frame_rms = rms(frame)
        self._update_noise_floor(frame_rms)
        threshold = max(self.noise_floor * self.config.energy_multiplier, 0.003)

        midi = hz_to_midi(pitch_hz) if pitch_hz else None
        voiced = midi is not None and frame_rms >= threshold

        if voiced:
            if self.active is None:
                self.active = _ActiveNote(start_s=time_s, last_voiced_s=time_s)
            self.active.last_voiced_s = time_s
            self.active.midi_values.append(midi)
        else:
            if self.active is not None and (time_s - self.active.last_voiced_s) >= self.config.release_s:
                note = self._finalize_active()
                if note:
                    notes.append(note)

        return notes

    def flush(self) -> List[UserNote]:
        if self.active is None:
            return []
        note = self._finalize_active()
        return [note] if note else []

    def _finalize_active(self) -> Optional[UserNote]:
        if self.active is None:
            return None
        end_s = self.active.last_voiced_s
        start_s = self.active.start_s
        duration = end_s - start_s
        midi_values = self.active.midi_values
        self.active = None

        if duration < self.config.min_note_s or not midi_values:
            return None

        midi = float(np.median(midi_values))
        return UserNote(start_s=start_s, end_s=end_s, midi=midi)

    def _update_noise_floor(self, frame_rms: float) -> None:
        if self.noise_floor == 0.0:
            self.noise_floor = frame_rms
            return
        alpha = 0.02
        self.noise_floor = (1.0 - alpha) * self.noise_floor + alpha * frame_rms
