from __future__ import annotations

import argparse
import queue
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

from .config import AudioConfig, NoteTrackingConfig, ScoringConfig
from .lyrics import LyricLine
from .pitch import PitchEstimator
from .scoring import ScoreBreakdown, score_notes
from .song import Song
from .tracking import NoteTracker, UserNote
from .ui import PygameUI, UIState


class SongClock:
    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self.time_s = 0.0

    def advance(self, frames: int) -> float:
        current = self.time_s
        self.time_s += frames / self.sample_rate
        return current

    def nudge(self, target_time_s: float) -> None:
        drift = target_time_s - self.time_s
        self.time_s += drift * 0.05


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Karaoke com nota (Pi 3)")
    parser.add_argument("--song", required=True, help="Pasta da musica dentro de songs/")
    parser.add_argument("--fullscreen", action="store_true", help="Tela cheia")
    parser.add_argument("--headless", action="store_true", help="Sem UI/sem playback")
    parser.add_argument("--device", help="Dispositivo de entrada de audio (indice ou nome)")
    parser.add_argument("--samplerate", type=int, default=44100, help="Sample rate")
    parser.add_argument("--blocksize", type=int, default=1024, help="Tamanho do bloco de audio")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    song = Song.from_dir(Path(args.song))

    audio_cfg = AudioConfig(sample_rate=args.samplerate, block_size=args.blocksize)
    tracking_cfg = NoteTrackingConfig()
    scoring_cfg = ScoringConfig()

    pitch_estimator = PitchEstimator(
        sample_rate=audio_cfg.sample_rate,
        min_freq=audio_cfg.min_freq,
        max_freq=audio_cfg.max_freq,
        corr_threshold=audio_cfg.corr_threshold,
    )
    tracker = NoteTracker(tracking_cfg)

    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

    def audio_callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            return
        audio_queue.put(indata.copy())

    stream = sd.InputStream(
        channels=audio_cfg.channels,
        samplerate=audio_cfg.sample_rate,
        blocksize=audio_cfg.block_size,
        device=args.device,
        callback=audio_callback,
    )

    ui: Optional[PygameUI] = None
    if not args.headless:
        ui = PygameUI(fullscreen=args.fullscreen)
        import pygame

        pygame.mixer.init(frequency=audio_cfg.sample_rate)
        pygame.mixer.music.load(str(song.audio_path))

    user_notes: list[UserNote] = []
    last_scored_count = -1
    breakdown = ScoreBreakdown(total=0.0, pitch=0.0, rhythm=0.0, matched=0, total_notes=len(song.melody.notes))
    clock = SongClock(audio_cfg.sample_rate)
    playback_started_at = None

    with stream:
        if not args.headless:
            import pygame

            pygame.mixer.music.play()
            playback_started_at = time.perf_counter()
        else:
            playback_started_at = time.perf_counter()

        running = True
        while running:
            song_time = _get_song_time(playback_started_at, ui)
            if song_time is not None:
                clock.nudge(song_time)

            while not audio_queue.empty():
                frame = audio_queue.get()
                mono = frame[:, 0]
                frame_time = clock.advance(len(mono))
                estimate = pitch_estimator.estimate(mono)
                new_notes = tracker.process(frame_time, mono, estimate.hz)
                user_notes.extend(new_notes)

            if ui:
                current, next_line = song.lyrics.current_and_next(max(clock.time_s - song.audio_offset_s, 0.0))
                if len(user_notes) != last_scored_count:
                    breakdown = score_notes(song.melody.notes, user_notes, scoring_cfg)
                    last_scored_count = len(user_notes)
                state = _build_ui_state(song, current, next_line, breakdown)
                running = ui.update(state)
            else:
                time.sleep(0.01)

            if not args.headless:
                import pygame

                if not pygame.mixer.music.get_busy():
                    running = False

        user_notes.extend(tracker.flush())

    final_score = score_notes(song.melody.notes, user_notes, scoring_cfg)
    _print_final(final_score)
    if ui:
        ui.close()
    return 0


def _get_song_time(start_time: Optional[float], ui: Optional[PygameUI]) -> Optional[float]:
    if start_time is None:
        return None
    if ui is None:
        return time.perf_counter() - start_time
    import pygame

    pos_ms = pygame.mixer.music.get_pos()
    if pos_ms < 0:
        return None
    return pos_ms / 1000.0


def _build_ui_state(
    song: Song,
    current: Optional[LyricLine],
    next_line: Optional[LyricLine],
    breakdown: ScoreBreakdown,
) -> UIState:
    return UIState(
        title=song.title,
        artist=song.artist,
        current_line=current.text if current else "",
        next_line=next_line.text if next_line else "",
        score_total=breakdown.total,
        score_pitch=breakdown.pitch,
        score_rhythm=breakdown.rhythm,
        notes_done=breakdown.matched,
        notes_total=breakdown.total_notes,
    )


def _print_final(breakdown: ScoreBreakdown) -> None:
    print("")
    print("Resultado final:")
    print(f"  Total:    {breakdown.total:05.1f}")
    print(f"  Afinacao: {breakdown.pitch:05.1f}")
    print(f"  Ritmo:    {breakdown.rhythm:05.1f}")
    print(f"  Notas:    {breakdown.matched}/{breakdown.total_notes}")


if __name__ == "__main__":
    raise SystemExit(main())
