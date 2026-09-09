"""Полоска внизу экрана с живой волной записи."""
from __future__ import annotations

import math
import random

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QFont
from PySide6.QtWidgets import QWidget, QApplication

from . import theme

BAR_COUNT = 48

STATE_TEXT = {
    "recording": "Запись… отпустите клавишу, чтобы вставить",
    "processing": "Распознаю…",
    "done": "Готово",
    "error": "Ошибка",
    "idle": "",
}


class WaveOverlay(QWidget):
    """Безрамочное окно поверх всех окон, не забирает фокус ввода."""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.state = "idle"
        self.message = ""
        self.level = 0.0
        self._levels = [0.06] * BAR_COUNT
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_overlay)

        self._resize_to_screen()

    # -- геометрия -----------------------------------------
    def _resize_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        width = min(720, int(geo.width() * 0.55))
        height = 92
        x = geo.x() + (geo.width() - width) // 2
        y = geo.y() + geo.height() - height - 48
        self.setGeometry(x, y, width, height)

    # -- управление --------------------------------------
    def show_state(self, state: str, message: str = "", auto_hide_ms: int = 0) -> None:
        self.state = state
        self.message = message or STATE_TEXT.get(state, "")
        self._resize_to_screen()
        self._hide_timer.stop()
        if not self.isVisible():
            self.show()
        self.raise_()
        if not self._timer.isActive():
            self._timer.start()
        if auto_hide_ms:
            self._hide_timer.start(auto_hide_ms)
        self.update()

    def hide_overlay(self) -> None:
        self._timer.stop()
        self.state = "idle"
        self.level = 0.0
        self._levels = [0.06] * BAR_COUNT
        self.hide()

    def set_level(self, level: float) -> None:
        self.level = max(0.0, min(1.0, float(level)))

    # -- анимация ----------------------------------------
    def _tick(self) -> None:
        self._phase += 0.22
        if self.state == "recording":
            target = max(0.08, self.level)
            self._levels.pop(0)
            jitter = random.uniform(0.72, 1.0)
            self._levels.append(min(1.0, target * jitter))
        elif self.state == "processing":
            self._levels = [
                0.22 + 0.20 * math.sin(self._phase + index * 0.35)
                for index in range(BAR_COUNT)
            ]
        else:
            self._levels = [max(0.05, value * 0.82) for value in self._levels]
        self.update()

    # -- отрисовка ---------------------------------------
    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)

        painter.fillPath(path, QColor(theme.PANEL))
        border = QColor(theme.GREEN_DEEP)
        if self.state == "recording":
            border = QColor(theme.GREEN)
        elif self.state == "error":
            border = QColor(theme.ERROR)
        painter.setPen(border)
        painter.drawPath(path)

        accent = QColor(theme.GREEN)
        if self.state == "error":
            accent = QColor(theme.ERROR)
        elif self.state == "processing":
            accent = QColor(theme.GREEN_DIM)

        # точка-индикатор
        painter.setBrush(accent)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(22, 26, 10, 10))

        # волна
        left = 46.0
        right = self.width() - 22.0
        available = right - left
        bar_width = max(2.0, available / (BAR_COUNT * 1.9))
        gap = (available - bar_width * BAR_COUNT) / max(1, BAR_COUNT - 1)
        center_y = 32.0
        max_height = 26.0

        gradient = QLinearGradient(left, 0, right, 0)
        gradient.setColorAt(0.0, QColor(theme.GREEN_DIM))
        gradient.setColorAt(0.5, accent)
        gradient.setColorAt(1.0, QColor(theme.GREEN_DIM))
        painter.setBrush(gradient)

        for index, value in enumerate(self._levels):
            height = max(3.0, float(value) * max_height * 2)
            x = left + index * (bar_width + gap)
            bar = QRectF(x, center_y - height / 2, bar_width, height)
            painter.drawRoundedRect(bar, bar_width / 2, bar_width / 2)

        # подпись
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT_DIM if self.state != "error" else theme.ERROR))
        painter.drawText(
            QRectF(46, 56, self.width() - 68, 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            self.message,
        )
        painter.end()
