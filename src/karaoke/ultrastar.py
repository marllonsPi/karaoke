from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class NoteToken:
    kind: str
    start: int
    duration: int
    pitch: int
    text: str
    line_index: int


def import_song(
    source: Path,
    dest: Path,
    txt: Optional[str] = None,
    ticks_per_beat: int = 4,
    include_freestyle: bool = False,
    relative: bool = False,
    audio_mode: str = "symlink",
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    txt_path = _find_txt(source, txt)
    headers, tokens, line_bases = _parse_ultrastar(txt_path)

    bpm = _parse_float(headers.get("BPM"))
    if bpm is None or bpm <= 0:
        raise ValueError("BPM invalido ou ausente no arquivo UltraStar (#BPM).")

    gap_ms = _parse_float(headers.get("GAP")) or 0.0
    gap_s = gap_ms / 1000.0

    use_relative = relative or headers.get("RELATIVE", "").upper() == "YES"
    notes = _convert_notes(
        tokens,
        line_bases,
        bpm=bpm,
        ticks_per_beat=ticks_per_beat,
        gap_s=gap_s,
        include_freestyle=include_freestyle,
        relative=use_relative,
    )

    lyrics = _convert_lyrics(
        tokens,
        line_bases,
        bpm=bpm,
        ticks_per_beat=ticks_per_beat,
        gap_s=gap_s,
        relative=use_relative,
    )

    _write_melody_csv(dest / "melody.csv", notes)
    _write_lyrics_lrc(dest / "lyrics.lrc", lyrics)
    _write_meta_json(dest / "meta.json", headers)

    audio_file = headers.get("MP3") or headers.get("AUDIO")
    if audio_file and audio_mode != "none":
        src_audio = (source / audio_file).resolve()
        if src_audio.exists():
            _handle_audio(src_audio, dest, audio_mode)


def _find_txt(source: Path, explicit: Optional[str]) -> Path:
    if explicit:
        path = (source / explicit).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Nao achei {path}")
        return path

    candidates = sorted(p for p in source.glob("*.txt") if p.is_file())
    if not candidates:
        raise FileNotFoundError("Nao achei arquivo .txt UltraStar na pasta fonte.")
    if len(candidates) > 1:
        raise ValueError("Mais de um .txt encontrado. Use --txt para escolher.")
    return candidates[0]


def _parse_ultrastar(path: Path) -> Tuple[Dict[str, str], List[NoteToken], Dict[int, int]]:
    headers: Dict[str, str] = {}
    tokens: List[NoteToken] = []
    line_bases: Dict[int, int] = {0: 0}
    line_index = 0

    for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            key, _, value = line[1:].partition(":")
            headers[key.strip().upper()] = value.strip()
            continue

        tag = line[0]
        if tag in (":", "*", "F"):
            parts = line.split(" ", 4)
            if len(parts) < 4:
                continue
            start = int(parts[1])
            duration = int(parts[2])
            pitch = int(parts[3])
            text = parts[4] if len(parts) > 4 else ""
            tokens.append(NoteToken(tag, start, duration, pitch, text, line_index))
        elif tag == "-":
            parts = line.split()
            if len(parts) > 1:
                try:
                    line_bases[line_index + 1] = int(parts[1])
                except ValueError:
                    pass
            line_index += 1
        elif tag == "E":
            break

    return headers, tokens, line_bases


def _convert_notes(
    tokens: List[NoteToken],
    line_bases: Dict[int, int],
    bpm: float,
    ticks_per_beat: int,
    gap_s: float,
    include_freestyle: bool,
    relative: bool,
) -> List[Tuple[float, float, int]]:
    notes: List[Tuple[float, float, int]] = []
    for token in tokens:
        if token.kind == "F" and not include_freestyle:
            continue
        abs_start = _absolute_ticks(token, line_bases, relative)
        start_s = _ticks_to_seconds(abs_start, bpm, ticks_per_beat) + gap_s
        duration_s = _ticks_to_seconds(token.duration, bpm, ticks_per_beat)
        notes.append((start_s, duration_s, token.pitch))
    return notes


def _convert_lyrics(
    tokens: List[NoteToken],
    line_bases: Dict[int, int],
    bpm: float,
    ticks_per_beat: int,
    gap_s: float,
    relative: bool,
) -> List[Tuple[float, str]]:
    lines: Dict[int, List[Tuple[float, str]]] = {}
    for token in tokens:
        abs_start = _absolute_ticks(token, line_bases, relative)
        start_s = _ticks_to_seconds(abs_start, bpm, ticks_per_beat) + gap_s
        lines.setdefault(token.line_index, []).append((start_s, token.text))

    output: List[Tuple[float, str]] = []
    for _, items in sorted(lines.items(), key=lambda item: item[0]):
        items.sort(key=lambda item: item[0])
        line_start_s = items[0][0]
        text = ""
        for _, syllable in items:
            cleaned = _clean_syllable(syllable)
            if not cleaned:
                continue
            if cleaned.startswith("-"):
                text = text + cleaned[1:]
            elif text:
                text = text + " " + cleaned
            else:
                text = cleaned
        if text.strip():
            output.append((line_start_s, text.strip()))

    return output


def _write_melody_csv(path: Path, notes: List[Tuple[float, float, int]]) -> None:
    lines = ["start_s,duration_s,midi"]
    for start_s, duration_s, midi in notes:
        lines.append(f"{start_s:.3f},{duration_s:.3f},{midi}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_lyrics_lrc(path: Path, lines: List[Tuple[float, str]]) -> None:
    output = []
    for time_s, text in lines:
        mm = int(time_s // 60)
        ss = time_s - mm * 60
        output.append(f"[{mm:02d}:{ss:05.2f}]{text}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _write_meta_json(path: Path, headers: Dict[str, str]) -> None:
    data = {
        "title": headers.get("TITLE") or "",
        "artist": headers.get("ARTIST") or "",
        "audio_offset_s": 0.0,
        "source": "ultrastar",
    }
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _handle_audio(src: Path, dest: Path, mode: str) -> None:
    ext = src.suffix.lower()
    target = dest / f"audio{ext}"
    if target.exists():
        return
    if mode == "copy":
        target.write_bytes(src.read_bytes())
    elif mode == "symlink":
        os.symlink(src, target)


def _clean_syllable(syllable: str) -> str:
    text = syllable.strip()
    if text in ("_", "~"):
        return ""
    return text


def _parse_float(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    value = raw.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _absolute_ticks(token: NoteToken, line_bases: Dict[int, int], relative: bool) -> int:
    if not relative:
        return token.start
    base = line_bases.get(token.line_index, 0)
    return base + token.start


def _ticks_to_seconds(ticks: int, bpm: float, ticks_per_beat: int) -> float:
    return (ticks / ticks_per_beat) * (60.0 / bpm)
