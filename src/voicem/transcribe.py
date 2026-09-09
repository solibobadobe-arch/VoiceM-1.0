"""Локальная бесплатная модель распознавания (faster-whisper / CTranslate2)."""
from __future__ import annotations

import threading

import numpy as np

from .config import model_dir
from .filler import clean_text


class Transcriber:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._model = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    def load(self) -> bool:
        """Загружает модель из папки, которая ставится вместе с программой."""
        with self._lock:
            if self._model is not None:
                return True
            path = model_dir(self.cfg)
            if path is None:
                self.last_error = (
                    "Локальная модель не найдена. Переустановите VoiceM "
                    "или задайте путь в VOICEM_MODEL_DIR."
                )
                return False
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    str(path),
                    device="cpu",
                    compute_type=self.cfg.get("compute_type", "int8"),
                    local_files_only=True,
                )
                self.last_error = None
                return True
            except Exception as exc:
                self.last_error = f"Не удалось загрузить модель: {exc}"
                self._model = None
                return False

    def transcribe(self, audio: np.ndarray) -> str:
        if audio is None or audio.size == 0:
            return ""
        if not self.load():
            return ""

        language = self.cfg.get("language") or None
        if language in ("auto", ""):
            language = None

        try:
            segments, _info = self._model.transcribe(
                audio.astype(np.float32),
                language=language,
                beam_size=int(self.cfg.get("beam_size", 1)),
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
                condition_on_previous_text=False,
                temperature=0.0,
                no_speech_threshold=0.6,
            )
            raw = " ".join(segment.text.strip() for segment in segments)
        except Exception as exc:
            self.last_error = f"Ошибка распознавания: {exc}"
            return ""

        return clean_text(
            raw,
            remove_fillers=bool(self.cfg.get("remove_fillers", True)),
            punctuation=bool(self.cfg.get("auto_punctuation", True)),
        )
