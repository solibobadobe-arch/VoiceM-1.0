"""Запись звука с микрофона + уровни для визуализации волны."""
from __future__ import annotations

import queue
import threading
from typing import Callable

import numpy as np

try:
    import sounddevice as sd
except Exception:  # pragma: no cover
    sd = None


class Recorder:
    """Пишет моно 16 kHz float32 и отдаёт уровень громкости для полоски волн."""

    def __init__(
        self,
        sample_rate: int = 16000,
        on_level: Callable[[float], None] | None = None,
        device: int | None = None,
    ):
        self.sample_rate = sample_rate
        self.on_level = on_level
        self.device = device
        self._chunks: list[np.ndarray] = []
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream = None
        self._lock = threading.Lock()
        self.recording = False
        self.error: str | None = None

    def _callback(self, indata, frames, time_info, status):  # noqa: ANN001
        data = np.asarray(indata, dtype=np.float32).reshape(-1).copy()
        self._queue.put(data)
        if self.on_level is not None:
            level = float(np.sqrt(np.mean(np.square(data))) if data.size else 0.0)
            self.on_level(min(1.0, level * 6.0))

    def start(self) -> bool:
        if self.recording:
            return True
        if sd is None:
            self.error = "Аудио-устройство недоступно"
            return False
        with self._lock:
            self._chunks.clear()
            while not self._queue.empty():
                self._queue.get_nowait()
            try:
                kwargs = {
                    "samplerate": self.sample_rate,
                    "channels": 1,
                    "dtype": "float32",
                    "blocksize": 1024,
                    "callback": self._callback,
                }
                if self.device is not None:
                    kwargs["device"] = self.device
                self._stream = sd.InputStream(**kwargs)
                self._stream.start()
            except Exception as exc:  # микрофон занят/не найден
                self.error = f"Микрофон недоступен: {exc}"
                self._stream = None
                return False
            self.recording = True
            self.error = None
            return True

    def stop(self) -> np.ndarray:
        with self._lock:
            self.recording = False
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            while not self._queue.empty():
                self._chunks.append(self._queue.get_nowait())
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks)
            self._chunks.clear()
            return audio

    def duration(self, audio: np.ndarray) -> float:
        return float(len(audio)) / float(self.sample_rate or 1)
