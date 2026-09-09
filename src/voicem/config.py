"""Конфигурация VoiceM."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "VoiceM"

DEFAULTS = {
    # "hold" — говорить, пока клавиша зажата; "toggle" — нажал/отпустил для старта и стопа
    "mode": "hold",
    # Горячая клавиша. По умолчанию правый Alt
    "hotkey": "right alt",
    "language": "ru",
    "model": "small",
    "compute_type": "int8",
    "beam_size": 1,
    "remove_fillers": True,
    "auto_punctuation": True,
    "insert_mode": "paste",  # paste | type
    "sample_rate": 16000,
    "min_seconds": 0.35,
    "max_seconds": 120,
    "sound_feedback": False,
    # —— настройки окна и системы (1.1.0) ——
    "input_device": None,  # None = устройство по умолчанию
    "show_overlay": True,
    "close_to_tray": True,
    "keep_history": True,
    "start_minimized": False,
    "autostart": False,
    "seen_welcome": False,
}


def app_data_dir() -> Path:
    base = os.getenv("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def base_dir() -> Path:
    """Папка, где лежит приложение (рядом с exe или корень репозитория)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def config_path() -> Path:
    return app_data_dir() / "config.json"


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    path = config_path()
    if path.exists():
        try:
            cfg.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        config_path().write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def model_dir(cfg: dict) -> Path | None:
    """Находит локальную модель, вшитую в установщик."""
    name = cfg.get("model", "small")
    candidates = [
        os.getenv("VOICEM_MODEL_DIR"),
        base_dir() / "models" / f"faster-whisper-{name}",
        base_dir() / "_internal" / "models" / f"faster-whisper-{name}",
        app_data_dir() / "models" / f"faster-whisper-{name}",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if (path / "model.bin").exists():
            return path
    return None


def log_path() -> Path:
    return app_data_dir() / "voicem.log"
