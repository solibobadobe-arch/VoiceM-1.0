"""Вставка текста в активное поле ввода любой программы Windows."""
from __future__ import annotations

import time

try:
    import pyperclip
except Exception:  # pragma: no cover
    pyperclip = None

try:
    import keyboard
except Exception:  # pragma: no cover
    keyboard = None


def _paste(text: str) -> bool:
    """Через буфер обмена + Ctrl+V — быстро и работает с кириллицей."""
    if pyperclip is None or keyboard is None:
        return False
    try:
        backup = None
        try:
            backup = pyperclip.paste()
        except Exception:
            backup = None

        pyperclip.copy(text)
        time.sleep(0.05)
        keyboard.send("ctrl+v")
        time.sleep(0.15)

        if backup is not None:
            try:
                pyperclip.copy(backup)
            except Exception:
                pass
        return True
    except Exception:
        return False


def _type(text: str) -> bool:
    if keyboard is None:
        return False
    try:
        keyboard.write(text, delay=0.005)
        return True
    except Exception:
        return False


def insert_text(text: str, mode: str = "paste") -> bool:
    """Вставляет текст туда, где сейчас курсор."""
    if not text:
        return False
    if mode == "type":
        return _type(text) or _paste(text)
    return _paste(text) or _type(text)
