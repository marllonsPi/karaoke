from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class PitchEstimate:
    hz: Optional[float]
    confidence: float


class PitchEstimator:
    def __init__(self, sample_rate: int, min_freq: float, max_freq: float, corr_threshold: float):
        self.sample_rate = sample_rate
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.corr_threshold = corr_threshold

    def estimate(self, frame: np.ndarray) -> PitchEstimate:
        if frame.size == 0:
            return PitchEstimate(None, 0.0)

        x = frame.astype(np.float32)
        x = x - np.mean(x)
        peak = np.max(np.abs(x))
        if peak < 1e-4:
            return PitchEstimate(None, 0.0)

        window = np.hanning(len(x))
        x = x * window

        spectrum = np.fft.rfft(x)
        corr = np.fft.irfft(np.abs(spectrum) ** 2)
        corr = corr[: len(corr) // 2]
        if corr[0] <= 1e-9:
            return PitchEstimate(None, 0.0)
        corr = corr / corr[0]

        min_lag = int(self.sample_rate / self.max_freq)
        max_lag = int(self.sample_rate / self.min_freq)
        max_lag = min(max_lag, len(corr) - 1)
        if max_lag <= min_lag + 2:
            return PitchEstimate(None, 0.0)

        search = corr[min_lag:max_lag]
        lag = int(np.argmax(search)) + min_lag
        confidence = float(corr[lag])
        if confidence < self.corr_threshold:
            return PitchEstimate(None, confidence)

        if 1 <= lag < len(corr) - 1:
            y0, y1, y2 = corr[lag - 1], corr[lag], corr[lag + 1]
            denom = 2.0 * (2.0 * y1 - y0 - y2)
            if abs(denom) > 1e-6:
                lag = lag + (y0 - y2) / denom

        hz = self.sample_rate / lag if lag > 0 else None
        return PitchEstimate(hz, confidence)
