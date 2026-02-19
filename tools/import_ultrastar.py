#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from karaoke.ultrastar import import_song  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importa musica no formato UltraStar para o karaoke.")
    parser.add_argument("--source", required=True, help="Pasta com o arquivo .txt UltraStar")
    parser.add_argument("--dest", required=True, help="Pasta de destino em songs/")
    parser.add_argument("--txt", help="Arquivo .txt especifico (se houver mais de um)")
    parser.add_argument("--ticks-per-beat", type=int, default=4, help="Unidades UltraStar por batida")
    parser.add_argument("--include-freestyle", action="store_true", help="Inclui notas 'F' na melodia")
    parser.add_argument("--relative", action="store_true", help="Trata timings como relativos a linha")
    parser.add_argument("--audio-mode", choices=["symlink", "copy", "none"], default="symlink")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import_song(
        source=Path(args.source),
        dest=Path(args.dest),
        txt=args.txt,
        ticks_per_beat=args.ticks_per_beat,
        include_freestyle=args.include_freestyle,
        relative=args.relative,
        audio_mode=args.audio_mode,
    )
    print("Importacao concluida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
