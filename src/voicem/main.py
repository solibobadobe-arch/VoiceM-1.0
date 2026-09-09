"""VoiceM — голосовой ввод в любое поле ввода Windows."""
from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import system_access, theme
from .audio import Recorder
from .config import load_config, log_path, model_dir, save_config
from .hotkey import HotkeyListener
from .inserter import insert_text
from .overlay import WaveOverlay
from .transcribe import Transcriber
from .window import MainWindow


def setup_logging() -> None:
    logging.basicConfig(
        filename=str(log_path()),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


class Bridge(QObject):
    """Передаёт события из фоновых потоков в UI-поток."""

    started = Signal()
    level = Signal(float)
    processing = Signal()
    finished = Signal(str)
    failed = Signal(str)
    cancelled = Signal()
    model_ready = Signal(bool, str)


def app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(theme.BLACK))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.GREEN))
    painter.drawRoundedRect(26, 12, 12, 26, 6, 6)
    painter.setBrush(QColor(theme.GREEN_DIM))
    painter.drawRoundedRect(20, 40, 24, 4, 2, 2)
    painter.drawRoundedRect(30, 44, 4, 8, 2, 2)
    painter.end()
    return QIcon(pixmap)


class VoiceMApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = load_config()
        self.bridge = Bridge()
        self.overlay = WaveOverlay()
        self.transcriber = Transcriber(self.cfg)
        self.recorder = Recorder(
            sample_rate=int(self.cfg.get("sample_rate", 16000)),
            on_level=self.bridge.level.emit,
            device=self.cfg.get("input_device"),
        )
        self.busy = False

        # главное окно с бургер-меню
        self.window = MainWindow(self.cfg)
        self.window.setWindowIcon(app_icon())
        self.window.settings_changed.connect(self._on_settings_changed)
        self.window.hotkey_changed.connect(self._rebind_hotkey)
        self.window.request_quit.connect(self._quit)

        self.bridge.started.connect(self._on_started)
        self.bridge.level.connect(self.overlay.set_level)
        self.bridge.processing.connect(self._on_processing)
        self.bridge.finished.connect(self._on_finished)
        self.bridge.failed.connect(self._on_failed)
        self.bridge.cancelled.connect(self._on_cancelled)
        self.bridge.model_ready.connect(self.window.set_model_state)

        self.tray = QSystemTrayIcon(app_icon(), app)
        self.tray.setToolTip(self._tooltip())
        self.tray.setContextMenu(self._menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self.listener = HotkeyListener(
            hotkey=self.cfg.get("hotkey", "right alt"),
            mode=self.cfg.get("mode", "hold"),
            on_start=self._start_recording,
            on_stop=self._stop_recording,
            on_cancel=self._cancel_recording,
        )

        threading.Thread(target=self._warm_up, daemon=True).start()

    # -- служебное ---------------------------------------
    def _tooltip(self) -> str:
        return (
            f"VoiceM — голосовой ввод\n"
            f"Клавиша: {self.cfg.get('hotkey')} ({self.cfg.get('mode')})"
        )

    def _menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet(theme.QSS)

        open_action = QAction("Открыть VoiceM", menu)
        open_action.triggered.connect(self._show_window)
        menu.addAction(open_action)

        settings_action = QAction("Настройки", menu)
        settings_action.triggered.connect(lambda: self._show_window("recognition"))
        menu.addAction(settings_action)

        access_action = QAction("Доступы Windows", menu)
        access_action.triggered.connect(lambda: self._show_window("access"))
        menu.addAction(access_action)

        menu.addSeparator()
        info = QAction(f"Клавиша: {self.cfg.get('hotkey')}", menu)
        info.setEnabled(False)
        menu.addAction(info)

        menu.addSeparator()
        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        return menu

    def _on_tray_activated(self, reason) -> None:  # noqa: ANN001
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def _show_window(self, page: str | None = None) -> None:
        if page:
            self.window.show_page(page)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.window.refresh_access()

    def _on_settings_changed(self, changes: dict) -> None:
        if "input_device" in changes:
            self.recorder.device = changes["input_device"]
        if "model" in changes or "language" in changes or "compute_type" in changes:
            self.transcriber.cfg = self.cfg

    def _rebind_hotkey(self, hotkey: str, mode: str) -> None:
        try:
            self.listener.stop()
        except Exception:
            pass
        self.listener = HotkeyListener(
            hotkey=hotkey or "right alt",
            mode=mode or "hold",
            on_start=self._start_recording,
            on_stop=self._stop_recording,
            on_cancel=self._cancel_recording,
        )
        if self.listener.start():
            self.window.set_status(f"Горячая клавиша: {hotkey.upper()}")
        else:
            self.window.set_status(self.listener.error or "Не удалось переназначить клавишу")
        self.tray.setToolTip(self._tooltip())
        self.tray.setContextMenu(self._menu())

    def _quit(self) -> None:
        try:
            self.listener.stop()
        except Exception:
            pass
        self.overlay.hide_overlay()
        self.tray.hide()
        self.cfg["close_to_tray"] = self.cfg.get("close_to_tray", True)
        save_config(self.cfg)
        self.app.quit()

    def _warm_up(self) -> None:
        if model_dir(self.cfg) is None:
            self.bridge.failed.emit("Модель не найдена — переустановите VoiceM")
            self.bridge.model_ready.emit(False, "Модель не найдена — переустановите VoiceM")
            return
        ok = self.transcriber.load()
        if ok is False:
            self.bridge.model_ready.emit(
                False, self.transcriber.last_error or "Модель не загрузилась"
            )
            return
        self.bridge.model_ready.emit(
            True,
            f"Модель распознавания готова: {self.cfg.get('model', 'small')} • локально, без интернета",
        )

    # -- запись -------------------------------------------
    def _overlay_enabled(self) -> bool:
        return bool(self.cfg.get("show_overlay", True))

    def _start_recording(self) -> None:
        if self.busy:
            return
        if not self.recorder.start():
            self.bridge.failed.emit(self.recorder.error or "Не удалось начать запись")
            return
        self.bridge.started.emit()

    def _stop_recording(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        duration = self.recorder.duration(audio)
        if duration < float(self.cfg.get("min_seconds", 0.35)):
            self.bridge.cancelled.emit()
            return
        self.busy = True
        self.bridge.processing.emit()
        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _cancel_recording(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
            self.bridge.cancelled.emit()

    def _process(self, audio) -> None:  # noqa: ANN001
        try:
            text = self.transcriber.transcribe(audio)
            if not text:
                self.bridge.failed.emit(
                    self.transcriber.last_error or "Речь не распознана"
                )
                return
            ok = insert_text(text, self.cfg.get("insert_mode", "paste"))
            if ok:
                self.bridge.finished.emit(text)
            else:
                self.bridge.failed.emit("Не удалось вставить текст")
        except Exception as exc:  # pragma: no cover
            logging.exception("processing failed")
            self.bridge.failed.emit(str(exc))
        finally:
            self.busy = False

    # -- UI-реакции --------------------------------------
    def _on_started(self) -> None:
        if self._overlay_enabled():
            self.overlay.show_state("recording")
        self.window.set_status("Запись…")

    def _on_processing(self) -> None:
        if self._overlay_enabled():
            self.overlay.show_state("processing")
        self.window.set_status("Распознаю…")

    def _on_finished(self, text: str) -> None:
        preview = text if len(text) <= 60 else text[:57] + "…"
        if self._overlay_enabled():
            self.overlay.show_state("done", preview, auto_hide_ms=1200)
        self.window.set_status("Готово")
        self.window.add_history(text)

    def _on_failed(self, message: str) -> None:
        logging.error(message)
        if self._overlay_enabled():
            self.overlay.show_state("error", message, auto_hide_ms=3500)
        self.window.set_status(message)

    def _on_cancelled(self) -> None:
        self.overlay.hide_overlay()
        self.window.set_status("Запись отменена")

    def run(self) -> int:
        if not self.listener.start():
            box = QMessageBox()
            box.setStyleSheet(theme.QSS)
            box.setWindowTitle("VoiceM")
            box.setText(self.listener.error or "Не удалось запустить горячую клавишу")
            box.exec()

        self.cfg["autostart"] = system_access.autostart_enabled()
        save_config(self.cfg)
        self.window.refresh_access()

        start_hidden = bool(self.cfg.get("start_minimized", False)) and bool(
            self.cfg.get("seen_welcome", False)
        )
        if start_hidden:
            if self._overlay_enabled():
                self.overlay.show_state("done", "VoiceM запущен", auto_hide_ms=1800)
        else:
            self.window.show()
            self.cfg["seen_welcome"] = True
            save_config(self.cfg)
        return self.app.exec()


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceM")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(theme.QSS)
    return VoiceMApp(app).run()
