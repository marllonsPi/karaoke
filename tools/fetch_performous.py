#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from karaoke.ultrastar import import_song  # noqa: E402


PERFORMOUS_SONGS_URL = "https://performous.org/songs"
SOURCEFORGE_RE = re.compile(r"https?://sourceforge\\.net/projects/performous/files/[^\\s\"']+?\\.zip/download")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa pacotes UltraStar do Performous e importa no karaoke.")
    parser.add_argument("--list", action="store_true", help="Lista os pacotes disponiveis")
    parser.add_argument("--package", action="append", help="Nome/alias do pacote (ex: libre, restricted)")
    parser.add_argument("--all", action="store_true", help="Baixa todos os pacotes encontrados")
    parser.add_argument("--dest", default="songs", help="Pasta destino das musicas")
    parser.add_argument("--cache", default=".cache/performous", help="Cache de downloads/extracao")
    parser.add_argument("--audio-mode", choices=["symlink", "copy", "none"], default="symlink")
    parser.add_argument("--ticks-per-beat", type=int, default=4, help="Unidades UltraStar por batida")
    parser.add_argument("--include-freestyle", action="store_true", help="Inclui notas 'F' na melodia")
    parser.add_argument("--relative", action="store_true", help="Forca timings relativos por linha")
    parser.add_argument("--max-songs", type=int, default=0, help="Limita quantidade de musicas importadas (0 = sem limite)")
    parser.add_argument("--refresh", action="store_true", help="Rebaixa e reextrai os pacotes")
    parser.add_argument("--json", action="store_true", help="Saida em JSON ao listar")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packages = fetch_packages()

    if args.list:
        _print_packages(packages, as_json=args.json)
        return 0

    if not args.all and not args.package:
        print("Use --list para ver pacotes ou informe --package.")
        return 2

    selected = select_packages(packages, args.package or [], args.all)
    if not selected:
        print("Nenhum pacote selecionado.")
        return 2

    dest_root = Path(args.dest)
    cache_root = Path(args.cache)
    cache_root.mkdir(parents=True, exist_ok=True)

    imported = 0
    for pkg in selected:
        zip_path = download_package(pkg, cache_root, refresh=args.refresh)
        extract_dir = extract_package(zip_path, cache_root, refresh=args.refresh)
        song_dirs = find_song_dirs(extract_dir)

        if not song_dirs:
            print(f"Nenhuma musica encontrada em {extract_dir}")
            continue

        for song_dir in song_dirs:
            song_name = song_dir.name
            target = dest_root / pkg["slug"] / song_name
            try:
                import_song(
                    source=song_dir,
                    dest=target,
                    ticks_per_beat=args.ticks_per_beat,
                    include_freestyle=args.include_freestyle,
                    relative=args.relative,
                    audio_mode=args.audio_mode,
                )
                imported += 1
            except Exception as exc:
                print(f"Falha ao importar {song_dir}: {exc}")

            if args.max_songs and imported >= args.max_songs:
                break
        if args.max_songs and imported >= args.max_songs:
            break

    print(f"Importacao finalizada. Musicas importadas: {imported}")
    return 0


def fetch_packages() -> List[Dict[str, str]]:
    html = _fetch_text(PERFORMOUS_SONGS_URL)

    urls = sorted(set(SOURCEFORGE_RE.findall(html)))
    packages: List[Dict[str, str]] = []
    for url in urls:
        filename = url.split("/")[-2] if url.endswith("/download") else Path(url).name
        slug = _slug_from_filename(filename)
        packages.append(
            {
                "slug": slug,
                "filename": filename,
                "url": url,
            }
        )
    return packages


def _slug_from_filename(filename: str) -> str:
    base = filename.lower().replace(".zip", "")
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    return base


def select_packages(packages: List[Dict[str, str]], names: Iterable[str], use_all: bool) -> List[Dict[str, str]]:
    if use_all:
        return packages

    name_set = {name.lower() for name in names}
    selected: List[Dict[str, str]] = []
    for pkg in packages:
        slug = pkg["slug"]
        if any(name in slug for name in name_set):
            selected.append(pkg)
    return selected


def download_package(pkg: Dict[str, str], cache_root: Path, refresh: bool) -> Path:
    zip_path = cache_root / pkg["filename"]
    if zip_path.exists() and not refresh:
        return zip_path

    print(f"Baixando {pkg['filename']}...")
    data = _fetch_bytes(pkg["url"])
    zip_path.write_bytes(data)
    return zip_path


def extract_package(zip_path: Path, cache_root: Path, refresh: bool) -> Path:
    extract_dir = cache_root / zip_path.stem
    if extract_dir.exists() and not refresh:
        return extract_dir

    if extract_dir.exists() and refresh:
        _remove_tree(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as archive:
        _safe_extract(archive, extract_dir)
    return extract_dir


def _safe_extract(archive: zipfile.ZipFile, dest: Path) -> None:
    for member in archive.infolist():
        target = dest / member.filename
        if not str(target.resolve()).startswith(str(dest.resolve())):
            raise ValueError(f"Zip inseguro: {member.filename}")
    archive.extractall(dest)


def find_song_dirs(root: Path) -> List[Path]:
    song_dirs = []
    for txt in root.rglob("*.txt"):
        song_dirs.append(txt.parent)
    song_dirs = sorted(set(song_dirs))
    return song_dirs


def _remove_tree(path: Path) -> None:
    for child in path.rglob("*"):
        if child.is_file() or child.is_symlink():
            child.unlink()
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_dir():
            child.rmdir()
    path.rmdir()


def _print_packages(packages: List[Dict[str, str]], as_json: bool) -> None:
    if as_json:
        print(json.dumps(packages, indent=2))
        return
    for pkg in packages:
        print(f"{pkg['slug']}: {pkg['url']}")


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "KaraokeFetcher/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def _fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "KaraokeFetcher/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


if __name__ == "__main__":
    raise SystemExit(main())
