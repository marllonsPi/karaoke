from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .lyrics import Lyrics
from .melody import Melody


@dataclass
class Song:
    root: Path
    audio_path: Path
    lyrics: Lyrics
    melody: Melody
    title: str
    artist: Optional[str] = None
    audio_offset_s: float = 0.0

    @classmethod
    def from_dir(cls, path: Path) -> "Song":
        root = path
        audio_path = None
        for name in ("audio.wav", "audio.ogg", "audio.mp3"):
            candidate = root / name
            if candidate.exists():
                audio_path = candidate
                break
        if audio_path is None:
            raise FileNotFoundError("Nao achei audio.wav/audio.ogg/audio.mp3")

        lyrics_path = root / "lyrics.lrc"
        melody_path = root / "melody.csv"
        if not lyrics_path.exists():
            raise FileNotFoundError("Nao achei lyrics.lrc")
        if not melody_path.exists():
            raise FileNotFoundError("Nao achei melody.csv")

        meta_path = root / "meta.json"
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

        title = meta.get("title", root.name)
        artist = meta.get("artist")
        audio_offset_s = float(meta.get("audio_offset_s", 0.0))

        return cls(
            root=root,
            audio_path=audio_path,
            lyrics=Lyrics.from_lrc(lyrics_path),
            melody=Melody.from_csv(melody_path),
            title=title,
            artist=artist,
            audio_offset_s=audio_offset_s,
        )
