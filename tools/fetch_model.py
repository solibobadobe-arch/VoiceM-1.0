"""Скачивание бесплатной локальной модели для вшивания в установщик."""
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
}

name = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("MODEL", "small")).strip()
if name not in REPOS:
    raise SystemExit(f"Неизвестная модель: {name}. Доступно: {', '.join(REPOS)}")

root = Path(__file__).resolve().parents[1] / "models" / f"faster-whisper-{name}"
root.mkdir(parents=True, exist_ok=True)

snapshot_download(
    repo_id=REPOS[name],
    local_dir=str(root),
    local_dir_use_symlinks=False,
    allow_patterns=[
        "model.bin",
        "config.json",
        "tokenizer.json",
        "vocabulary.txt",
        "vocabulary.json",
        "preprocessor_config.json",
    ],
)

if not (root / "model.bin").exists():
    raise SystemExit("model.bin не скачался")

print("model ready:", root)
