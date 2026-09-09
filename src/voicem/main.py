"""VoiceM — голосовой ввод в любое поле ввода Windows."""
from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import theme
from .audio import Recorder
from .config import config_path, load_config, log_path, model_dir, save_config
from .hotkey import HotkeyListener
from .inserter import insert_text
from .overlay import WaveOverlay
from .transcribe import Transcriber


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
        )
        self.busy = False

        self.bridge.started.connect(self._on_started)
        self.bridge.level.connect(self.overlay.set_level)
        self.bridge.processing.connect(self._on_processing)
        self.bridge.finished.connect(self._on_finished)
        self.bridge.failed.connect(self._on_failed)
        self.bridge.cancelled.connect(self._on_cancelled)

        self.tray = QSystemTrayIcon(app_icon(), app)
        self.tray.setToolTip(self._tooltip())
        self.tray.setContextMenu(self._menu())
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

        info = QAction(f"Клавиша: {self.cfg.get('hotkey')}", menu)
        info.setEnabled(False)
        menu.addAction(info)
        menu.addSeparator()

        mode_action = QAction(
            "Режим: удержание" if self.cfg.get("mode") == "hold" else "Режим: переключение",
            menu,
        )
        mode_action.setEnabled(False)
        menu.addAction(mode_action)

        fillers = QAction("Убирать слова-паразиты", menu)
        fillers.setCheckable(True)
        fillers.setChecked(bool(self.cfg.get("remove_fillers", True)))
        fillers.triggered.connect(self._toggle_fillers)
        menu.addAction(fillers)

        settings = QAction("Открыть файл настроек", menu)
        settings.triggered.connect(self._open_settings)
        menu.addAction(settings)

        about = QAction("О программе", menu)
        about.triggered.connect(self._about)
        menu.addAction(about)

        menu.addSeparator()
        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        return menu

    def _toggle_fillers(self, checked: bool) -> None:
        self.cfg["remove_fillers"] = bool(checked)
        save_config(self.cfg)

    def _open_settings(self) -> None:
        import os

        path = config_path()
        if not path.exists():
            save_config(self.cfg)
        try:
            os.startfile(str(path))  # noqa: S606
        except Exception:
            pass

    def _about(self) -> None:
        box = QMessageBox()
        box.setStyleSheet(theme.QSS)
        box.setWindowTitle("VoiceM")
        box.setText(
            "VoiceM 1.0.0\n\n"
            "Голосовой ввод в любое поле ввода.\n"
            f"Горячая клавиша: {self.cfg.get('hotkey')}\n"
            "Распознавание работает локально, без интернета."
        )
        box.exec()

    def _quit(self) -> None:
        self.listener.stop()
        self.overlay.hide_overlay()
        self.tray.hide()
        self.app.quit()

    def _warm_up(self) -> None:
        if model_dir(self.cfg) is None:
            self.bridge.failed.emit("Модель не найдена — переустановите VoiceM")
            return
        self.transcriber.load()

    # -- запись -------------------------------------------
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
        self.overlay.show_state("recording")

    def _on_processing(self) -> None:
        self.overlay.show_state("processing")

    def _on_finished(self, text: str) -> None:
        preview = text if len(text) <= 60 else text[:57] + "…"
        self.overlay.show_state("done", preview, auto_hide_ms=1200)

    def _on_failed(self, message: str) -> None:
        logging.error(message)
        self.overlay.show_state("error", message, auto_hide_ms=3500)

    def _on_cancelled(self) -> None:
        self.overlay.hide_overlay()

    def run(self) -> int:
        if not self.listener.start():
            box = QMessageBox()
            box.setStyleSheet(theme.QSS)
            box.setWindowTitle("VoiceM")
            box.setText(self.listener.error or "Не удалось запустить горячую клавишу")
            box.exec()
            return 1
        self.overlay.show_state("done", "VoiceM запущен", auto_hide_ms=1800)
        return self.app.exec()


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceM")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(theme.QSS)
    return VoiceMApp(app).run()
