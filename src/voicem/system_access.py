"""Доступы Windows: микрофон, автозапуск, права администратора."""
from __future__ import annotations

import os
import subprocess
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_KEY = "VoiceM"
MIC_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
    r"\ConsentStore\microphone"
)


def _winreg():
    try:
        import winreg

        return winreg
    except Exception:
        return None


def executable_path() -> str:
    """Путь, который нужно прописать в автозапуск."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "run.py"))
    return f'"{sys.executable}" "{script}"'


# -- автозапуск -----------------------------------------------
def autostart_enabled() -> bool:
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_KEY)
            return bool(value)
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Включает/выключает запуск вместе с Windows."""
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, executable_path())
            else:
                try:
                    winreg.DeleteValue(key, APP_KEY)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


# -- микрофон ------------------------------------------------
def microphone_allowed() -> bool | None:
    """True — разрешён, False — запрещён, None — неизвестно."""
    winreg = _winreg()
    if winreg is None:
        return None
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, MIC_KEY) as key:
                value, _ = winreg.QueryValueEx(key, "Value")
                if str(value).lower() == "deny":
                    return False
                if str(value).lower() == "allow":
                    return True
        except Exception:
            continue
    return None


def microphone_works() -> bool:
    """Фактическая проверка: удаётся ли открыть поток записи."""
    try:
        import sounddevice as sd

        with sd.InputStream(samplerate=16000, channels=1, dtype="float32"):
            return True
    except Exception:
        return False


def list_microphones() -> list[tuple[int, str]]:
    """Список устройств записи: [(индекс, имя)]."""
    try:
        import sounddevice as sd

        devices = []
        for index, device in enumerate(sd.query_devices()):
            if int(device.get("max_input_channels", 0)) > 0:
                devices.append((index, str(device.get("name", f"Устройство {index}"))))
        return devices
    except Exception:
        return []


# -- права --------------------------------------------------
def is_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def keyboard_hook_available() -> bool:
    """Проверяет, может ли приложение перехватывать клавиши."""
    try:
        import keyboard

        handler = keyboard.hook(lambda event: None, suppress=False)
        keyboard.unhook(handler)
        return True
    except Exception:
        return False


def restart_as_admin() -> bool:
    """Перезапускает VoiceM с правами администратора."""
    try:
        import ctypes

        if getattr(sys, "frozen", False):
            params = ""
            target = sys.executable
        else:
            target = sys.executable
            params = " ".join(f'"{arg}"' for arg in sys.argv)
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1)
        return int(result) > 32
    except Exception:
        return False


# -- окна настроек Windows ------------------------------------
SETTINGS_PAGES = {
    "microphone": "ms-settings:privacy-microphone",
    "sound": "ms-settings:sound",
    "startup": "ms-settings:startupapps",
    "privacy": "ms-settings:privacy",
    "notifications": "ms-settings:notifications",
}


def open_windows_settings(page: str) -> bool:
    uri = SETTINGS_PAGES.get(page, page)
    try:
        os.startfile(uri)  # noqa: S606
        return True
    except Exception:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", uri], shell=False)
            return True
        except Exception:
            return False


def open_path(path: str) -> bool:
    try:
        os.startfile(str(path))  # noqa: S606
        return True
    except Exception:
        return False
