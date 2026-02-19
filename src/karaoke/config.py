from dataclasses import dataclass


@dataclass
class AudioConfig:
    sample_rate: int = 44100
    block_size: int = 1024
    channels: int = 1
    min_freq: float = 80.0
    max_freq: float = 900.0
    corr_threshold: float = 0.35


@dataclass
class ScoringConfig:
    pitch_tolerance_cents: float = 80.0
    rhythm_tolerance_s: float = 0.25
    pitch_weight: float = 0.6
    rhythm_weight: float = 0.4


@dataclass
class NoteTrackingConfig:
    energy_multiplier: float = 3.0
    min_note_s: float = 0.12
    release_s: float = 0.15
