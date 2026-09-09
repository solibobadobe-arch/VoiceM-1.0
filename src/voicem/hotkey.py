"""Глобальная горячая клавиша: удержание или переключение."""
from __future__ import annotations

import threading
from typing import Callable

try:
    import keyboard
except Exception:  # pragma: no cover
    keyboard = None


class HotkeyListener:
    def __init__(
        self,
        hotkey: str,
        mode: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_cancel: Callable[[], None] | None = None,
    ):
        self.hotkey = hotkey or "right alt"
        self.mode = mode if mode in ("hold", "toggle") else "hold"
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_cancel = on_cancel
        self.active = False
        self.error: str | None = None
        self._lock = threading.Lock()
        self._hooked = False

    def start(self) -> bool:
        if keyboard is None:
            self.error = "Модуль клавиатуры недоступен"
            return False
        try:
            if self.mode == "toggle":
                keyboard.add_hotkey(self.hotkey, self._toggle, suppress=False)
            else:
                keyboard.on_press_key(self.hotkey, self._pressed, suppress=False)
                keyboard.on_release_key(self.hotkey, self._released, suppress=False)
            keyboard.on_press_key("esc", self._escape, suppress=False)
            self._hooked = True
            self.error = None
            return True
        except Exception as exc:
            self.error = (
                f"Не удалось перехватить клавишу '{self.hotkey}': {exc}. "
                "Попробуйте запустить VoiceM от имени администратора."
            )
            return False

    def stop(self) -> None:
        if keyboard is None or not self._hooked:
            return
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self._hooked = False

    # -- обработчики -------------------------------------
    def _pressed(self, event) -> None:  # noqa: ANN001
        with self._lock:
            if self.active:
                return
            self.active = True
        self.on_start()

    def _released(self, event) -> None:  # noqa: ANN001
        with self._lock:
            if not self.active:
                return
            self.active = False
        self.on_stop()

    def _toggle(self) -> None:
        with self._lock:
            self.active = not self.active
            started = self.active
        if started:
            self.on_start()
        else:
            self.on_stop()

    def _escape(self, event) -> None:  # noqa: ANN001
        with self._lock:
            if not self.active:
                return
            self.active = False
        if self.on_cancel is not None:
            self.on_cancel()
