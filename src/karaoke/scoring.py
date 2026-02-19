from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .config import ScoringConfig
from .melody import ReferenceNote
from .tracking import UserNote


@dataclass
class ScoreBreakdown:
    total: float
    pitch: float
    rhythm: float
    matched: int
    total_notes: int


def score_notes(
    references: List[ReferenceNote],
    users: List[UserNote],
    config: ScoringConfig,
) -> ScoreBreakdown:
    if not references:
        return ScoreBreakdown(0.0, 0.0, 0.0, 0, 0)

    used = [False] * len(users)
    pitch_scores: List[float] = []
    rhythm_scores: List[float] = []
    matched = 0

    for ref in references:
        match = _find_match(ref, users, used, config.rhythm_tolerance_s)
        if match is None:
            continue
        idx, user = match
        used[idx] = True
        matched += 1

        cents_error = abs(user.midi - ref.midi) * 100.0
        pitch_score = max(0.0, 1.0 - (cents_error / config.pitch_tolerance_cents))

        time_error = abs(user.start_s - ref.start_s)
        rhythm_score = max(0.0, 1.0 - (time_error / config.rhythm_tolerance_s))

        pitch_scores.append(pitch_score)
        rhythm_scores.append(rhythm_score)

    if matched == 0:
        return ScoreBreakdown(0.0, 0.0, 0.0, 0, len(references))

    pitch_avg = sum(pitch_scores) / matched
    rhythm_avg = sum(rhythm_scores) / matched
    total = (
        (pitch_avg * config.pitch_weight + rhythm_avg * config.rhythm_weight)
        / (config.pitch_weight + config.rhythm_weight)
    )

    return ScoreBreakdown(
        total=total * 100.0,
        pitch=pitch_avg * 100.0,
        rhythm=rhythm_avg * 100.0,
        matched=matched,
        total_notes=len(references),
    )


def _find_match(
    ref: ReferenceNote,
    users: List[UserNote],
    used: List[bool],
    tol: float,
) -> Optional[Tuple[int, UserNote]]:
    candidates: List[Tuple[int, UserNote, float]] = []
    ref_start = ref.start_s
    ref_end = ref.end_s

    for idx, user in enumerate(users):
        if used[idx]:
            continue
        if user.end_s < ref_start - tol:
            continue
        if user.start_s > ref_end + tol:
            continue
        delta = abs(user.start_s - ref_start)
        candidates.append((idx, user, delta))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[2])
    idx, user, _ = candidates[0]
    return idx, user
