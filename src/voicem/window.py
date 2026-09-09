"""Главное окно VoiceM: бургер-меню слева + страницы настроек."""
from __future__ import annotations

import threading
from datetime import datetime

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import system_access, theme
from .config import app_data_dir, config_path, log_path, save_config
from .widgets import Card, StatusDot, ToggleSwitch

DRAWER_WIDTH = 236

NAV_ITEMS = [
    ("home", "⌂   Главная"),
    ("recognition", "◉   Распознавание"),
    ("hotkey", "⌨   Горячая клавиша"),
    ("access", "⚿   Доступы Windows"),
    ("system", "⚙   Система"),
    ("history", "☷   История"),
    ("about", "ⓘ   О программе"),
]

LANGUAGES = [("Русский", "ru"), ("English", "en"), ("Автоопределение", "auto")]
MODELS = [
    ("tiny — самая быстрая", "tiny"),
    ("base — быстрая", "base"),
    ("small — баланс (рекомендуется)", "small"),
    ("medium — самая точная", "medium"),
]
MODES = [("Удержание клавиши", "hold"), ("Нажать / нажать снова", "toggle")]
INSERT_MODES = [("Вставка (быстро)", "paste"), ("Побуквенный ввод", "type")]


class BurgerButton(QPushButton):
    """Три полоски, которые превращаются в крестик."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("burger")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(42, 42)
        self._opened = False

    def set_opened(self, opened: bool) -> None:
        self._opened = bool(opened)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(theme.GREEN), 2.2, Qt.SolidLine, Qt.RoundCap))
        cx, cy = self.width() / 2, self.height() / 2
        if self._opened:
            painter.drawLine(int(cx - 7), int(cy - 7), int(cx + 7), int(cy + 7))
            painter.drawLine(int(cx - 7), int(cy + 7), int(cx + 7), int(cy - 7))
        else:
            for offset in (-7, 0, 7):
                painter.drawLine(int(cx - 9), int(cy + offset), int(cx + 9), int(cy + offset))
        painter.end()


class MainWindow(QWidget):
    """Окно настроек с выезжающей боковой менюшкой."""

    settings_changed = Signal(dict)
    hotkey_changed = Signal(str, str)
    request_quit = Signal()
    capture_done = Signal(str)

    def __init__(self, cfg: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("VoiceM")
        self.resize(900, 640)
        self.setMinimumSize(780, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_top_bar())

        self.body = QWidget()
        body_layout = QHBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        self.pages = QStackedWidget()
        body_layout.addWidget(self.pages, 1)
        root.addWidget(self.body, 1)

        self.drawer = self._build_drawer(self.body)
        self.drawer.move(-DRAWER_WIDTH, 0)
        self.drawer_open = False
        self._anim = QPropertyAnimation(self.drawer, b"geometry", self)
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._page_index: dict[str, int] = {}
        self._build_pages()
        self.capture_done.connect(self._on_capture_done)
        self.show_page("home")

    # ================= шапка =================
    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 18, 10)
        layout.setSpacing(14)

        self.burger = BurgerButton()
        self.burger.setToolTip("Меню")
        self.burger.clicked.connect(self.toggle_drawer)
        layout.addWidget(self.burger)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("VoiceM")
        title.setObjectName("appTitle")
        subtitle = QLabel("Голосовой ввод в любое поле • работает офлайн")
        subtitle.setObjectName("appSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        layout.addLayout(titles)
        layout.addStretch(1)

        self.top_status = QLabel("Готов к работе")
        self.top_status.setObjectName("status")
        layout.addWidget(self.top_status)

        hide_button = QPushButton("Свернуть в трей")
        hide_button.clicked.connect(self.hide)
        layout.addWidget(hide_button)
        return bar

    # ================= боковая менюшка =================
    def _build_drawer(self, parent: QWidget) -> QWidget:
        drawer = QWidget(parent)
        drawer.setObjectName("drawer")
        drawer.setFixedWidth(DRAWER_WIDTH)

        shadow = QGraphicsDropShadowEffect(drawer)
        shadow.setBlurRadius(40)
        shadow.setXOffset(6)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 190))
        drawer.setGraphicsEffect(shadow)

        layout = QVBoxLayout(drawer)
        layout.setContentsMargins(12, 18, 12, 16)
        layout.setSpacing(6)

        header = QLabel("Меню")
        header.setObjectName("drawerTitle")
        layout.addWidget(header)
        layout.addSpacing(8)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for key, label in NAV_ITEMS:
            button = QPushButton(label)
            button.setObjectName("navItem")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, k=key: self.show_page(k, close=True)
            )
            layout.addWidget(button)
            self.nav_group.addButton(button)
            self.nav_buttons[key] = button

        layout.addStretch(1)
        version_hint = QLabel("VoiceM 1.1.0 • локальная модель")
        version_hint.setObjectName("drawerHint")
        version_hint.setWordWrap(True)
        layout.addWidget(version_hint)

        quit_button = QPushButton("✕   Закрыть VoiceM")
        quit_button.setObjectName("navItem")
        quit_button.setCursor(Qt.PointingHandCursor)
        quit_button.clicked.connect(self.request_quit.emit)
        layout.addWidget(quit_button)
        return drawer

    def toggle_drawer(self) -> None:
        self.set_drawer(not self.drawer_open)

    def set_drawer(self, opened: bool) -> None:
        height = max(self.body.height(), 1)
        start = QRect(self.drawer.x(), 0, DRAWER_WIDTH, height)
        end_x = 0 if opened else -DRAWER_WIDTH
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(QRect(end_x, 0, DRAWER_WIDTH, height))
        self._anim.start()
        self.drawer_open = opened
        self.burger.set_opened(opened)
        self.drawer.raise_()

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        x = 0 if self.drawer_open else -DRAWER_WIDTH
        self.drawer.setGeometry(x, 0, DRAWER_WIDTH, max(self.body.height(), 1))

    # ================= страницы =================
    def _scrollable(self, widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(widget)
        return area

    def _page_shell(self, title: str, hint: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        if hint:
            sub = QLabel(hint)
            sub.setObjectName("pageHint")
            sub.setWordWrap(True)
            layout.addWidget(sub)
        return page, layout

    def _add_page(self, key: str, widget: QWidget) -> None:
        self._page_index[key] = self.pages.addWidget(widget)

    def show_page(self, key: str, close: bool = False) -> None:
        index = self._page_index.get(key)
        if index is not None:
            self.pages.setCurrentIndex(index)
        button = self.nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        if close and self.drawer_open:
            self.set_drawer(False)

    def _build_pages(self) -> None:
        self._add_page("home", self._scrollable(self._page_home()))
        self._add_page("recognition", self._scrollable(self._page_recognition()))
        self._add_page("hotkey", self._scrollable(self._page_hotkey()))
        self._add_page("system", self._scrollable(self._page_system()))
        self._add_page("access", self._scrollable(self._page_access()))
        self._add_page("history", self._scrollable(self._page_history()))
        self._add_page("about", self._scrollable(self._page_about()))

    # -- общее ------------------------------------------------
    def _set(self, key: str, value, restart: bool = False) -> None:  # noqa: ANN001
        self.cfg[key] = value
        save_config(self.cfg)
        self.settings_changed.emit({key: value})
        if restart:
            self.set_status("Сохранено — перезапустите VoiceM")
        else:
            self.set_status("Настройки сохранены")

    def _combo(self, items: list[tuple[str, str]], current: str) -> QComboBox:
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(current)
        if index >= 0:
            combo.setCurrentIndex(index)
        return combo

    def _row_with_dot(self, card: Card, dot: StatusDot, label: QLabel) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        row_layout.addWidget(dot)
        label.setObjectName("rowTitle")
        label.setWordWrap(True)
        row_layout.addWidget(label, 1)
        card.body().addWidget(row)

    # -- Главная ----------------------------------------------
    def _page_home(self) -> QWidget:
        page, layout = self._page_shell(
            "Главная", "Кликни в любое поле ввода, зажми клавишу и говори."
        )

        card = Card("Текущая горячая клавиша")
        self.home_hotkey = QLabel(str(self.cfg.get("hotkey", "right alt")).upper())
        self.home_hotkey.setObjectName("bigHotkey")
        card.body().addWidget(self.home_hotkey)
        self.home_mode = QLabel(self._mode_text())
        self.home_mode.setObjectName("rowHint")
        card.body().addWidget(self.home_mode)
        layout.addWidget(card)

        status_card = Card("Состояние")
        self.dot_model = StatusDot(None)
        self.dot_mic = StatusDot(None)
        self.dot_keys = StatusDot(None)
        self.label_model = QLabel("Модель распознавания: проверка…")
        self.label_mic = QLabel("Микрофон: проверка…")
        self.label_keys = QLabel("Перехват клавиш: проверка…")
        self._row_with_dot(status_card, self.dot_model, self.label_model)
        self._row_with_dot(status_card, self.dot_mic, self.label_mic)
        self._row_with_dot(status_card, self.dot_keys, self.label_keys)
        layout.addWidget(status_card)

        steps = Card("Как пользоваться")
        text = QLabel(
            "1.  Кликни в поле ввода — чат, браузер, Word, что угодно\n"
            "2.  Зажми горячую клавишу — внизу появится зелёная волна\n"
            "3.  Говори свободно — слова-паразиты уберутся сами\n"
            "4.  Отпусти клавишу — чистый текст вставится сам\n\n"
            "Esc во время записи — отмена."
        )
        text.setObjectName("rowHint")
        text.setWordWrap(True)
        steps.body().addWidget(text)
        layout.addWidget(steps)

        layout.addStretch(1)
        return page

    def _mode_text(self) -> str:
        if self.cfg.get("mode") == "toggle":
            return "Режим: нажать один раз — запись, нажать снова — вставка"
        return "Режим: держи клавишу, пока говоришь"

    # -- Распознавание ----------------------------------------
    def _page_recognition(self) -> QWidget:
        page, layout = self._page_shell("Распознавание", "Язык, модель и обработка текста.")

        card = Card("Речь")
        self.combo_language = self._combo(LANGUAGES, str(self.cfg.get("language", "ru")))
        self.combo_language.currentIndexChanged.connect(
            lambda: self._set("language", self.combo_language.currentData())
        )
        card.add_row("Язык распознавания", "На каком языке ты говоришь", self.combo_language)

        self.combo_model = self._combo(MODELS, str(self.cfg.get("model", "small")))
        self.combo_model.currentIndexChanged.connect(
            lambda: self._set("model", self.combo_model.currentData(), restart=True)
        )
        card.add_row(
            "Модель",
            "Чем больше — тем точнее, но медленнее. Требует перезапуска",
            self.combo_model,
        )
        layout.addWidget(card)

        clean = Card("Обработка текста")
        self.toggle_fillers = ToggleSwitch(bool(self.cfg.get("remove_fillers", True)))
        self.toggle_fillers.toggled.connect(lambda v: self._set("remove_fillers", v))
        clean.add_row(
            "Убирать слова-паразиты",
            "«э», «ну», «типа», «короче», «в общем», «uh», «um» и подобные",
            self.toggle_fillers,
        )
        self.toggle_punct = ToggleSwitch(bool(self.cfg.get("auto_punctuation", True)))
        self.toggle_punct.toggled.connect(lambda v: self._set("auto_punctuation", v))
        clean.add_row(
            "Автопунктуация", "Заглавные буквы и точка в конце фразы", self.toggle_punct
        )
        layout.addWidget(clean)

        insert = Card("Вставка текста")
        self.combo_insert = self._combo(
            INSERT_MODES, str(self.cfg.get("insert_mode", "paste"))
        )
        self.combo_insert.currentIndexChanged.connect(
            lambda: self._set("insert_mode", self.combo_insert.currentData())
        )
        insert.add_row(
            "Способ вставки",
            "Если где-то текст не вставляется — попробуй побуквенный ввод",
            self.combo_insert,
        )
        self.toggle_overlay = ToggleSwitch(bool(self.cfg.get("show_overlay", True)))
        self.toggle_overlay.toggled.connect(lambda v: self._set("show_overlay", v))
        insert.add_row(
            "Показывать полоску с волнами",
            "Зелёная плашка внизу экрана во время записи",
            self.toggle_overlay,
        )
        layout.addWidget(insert)

        layout.addStretch(1)
        return page

    # -- Горячая клавиша --------------------------------------
    def _page_hotkey(self) -> QWidget:
        page, layout = self._page_shell(
            "Горячая клавиша", "Какой клавишей запускать запись голоса."
        )

        card = Card("Клавиша")
        self.hotkey_label = QLabel(str(self.cfg.get("hotkey", "right alt")).upper())
        self.hotkey_label.setObjectName("bigHotkey")
        card.body().addWidget(self.hotkey_label)

        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        self.capture_button = QPushButton("Назначить клавишу")
        self.capture_button.setObjectName("primary")
        self.capture_button.clicked.connect(self._capture_hotkey)
        buttons_layout.addWidget(self.capture_button)
        reset_button = QPushButton("Сбросить на правый Alt")
        reset_button.clicked.connect(lambda: self._apply_hotkey("right alt"))
        buttons_layout.addWidget(reset_button)
        buttons_layout.addStretch(1)
        card.body().addWidget(buttons)

        self.capture_hint = QLabel("Нажми «Назначить» и нажми любую клавишу или сочетание.")
        self.capture_hint.setObjectName("rowHint")
        self.capture_hint.setWordWrap(True)
        card.body().addWidget(self.capture_hint)
        layout.addWidget(card)

        mode_card = Card("Режим работы")
        self.combo_mode = self._combo(MODES, str(self.cfg.get("mode", "hold")))
        self.combo_mode.currentIndexChanged.connect(self._change_mode)
        mode_card.add_row(
            "Как запускать запись",
            "Удержание — для коротких фраз, переключение — для длинных",
            self.combo_mode,
        )
        layout.addWidget(mode_card)

        layout.addStretch(1)
        return page

    def _change_mode(self) -> None:
        mode = self.combo_mode.currentData()
        self.cfg["mode"] = mode
        save_config(self.cfg)
        self.home_mode.setText(self._mode_text())
        self.hotkey_changed.emit(str(self.cfg.get("hotkey", "right alt")), str(mode))

    def _capture_hotkey(self) -> None:
        self.capture_button.setEnabled(False)
        self.capture_button.setText("Жду нажатия…")
        self.capture_hint.setText("Нажми любую клавишу или сочетание…")

        def worker() -> None:
            try:
                import keyboard

                hotkey = keyboard.read_hotkey(suppress=False)
            except Exception:
                hotkey = ""
            self.capture_done.emit(hotkey)

        threading.Thread(target=worker, daemon=True).start()

    def _on_capture_done(self, hotkey: str) -> None:
        self.capture_button.setEnabled(True)
        self.capture_button.setText("Назначить клавишу")
        if not hotkey:
            self.capture_hint.setText(
                "Не удалось считать клавишу. Запусти VoiceM от имени администратора."
            )
            return
        self._apply_hotkey(hotkey)

    def _apply_hotkey(self, hotkey: str) -> None:
        self.cfg["hotkey"] = hotkey
        save_config(self.cfg)
        self.hotkey_label.setText(hotkey.upper())
        self.home_hotkey.setText(hotkey.upper())
        self.capture_hint.setText(f"Готово: {hotkey.upper()}")
        self.hotkey_changed.emit(hotkey, str(self.cfg.get("mode", "hold")))

    # -- Доступы Windows -------------------------------------
    def _page_access(self) -> QWidget:
        page, layout = self._page_shell(
            "Доступы Windows",
            "Чтобы голосовой ввод работал, Windows должен разрешить микрофон и перехват клавиш.",
        )

        mic_card = Card("Микрофон")
        self.access_dot_mic = StatusDot(None)
        self.access_label_mic = QLabel("Проверка доступа…")
        self._row_with_dot(mic_card, self.access_dot_mic, self.access_label_mic)

        mic_buttons = QWidget()
        mic_layout = QHBoxLayout(mic_buttons)
        mic_layout.setContentsMargins(0, 0, 0, 0)
        mic_layout.setSpacing(10)
        open_mic = QPushButton("Открыть доступ к микрофону")
        open_mic.setObjectName("primary")
        open_mic.clicked.connect(lambda: system_access.open_windows_settings("microphone"))
        mic_layout.addWidget(open_mic)
        open_sound = QPushButton("Параметры звука")
        open_sound.clicked.connect(lambda: system_access.open_windows_settings("sound"))
        mic_layout.addWidget(open_sound)
        recheck = QPushButton("Проверить снова")
        recheck.clicked.connect(self.refresh_access)
        mic_layout.addWidget(recheck)
        mic_layout.addStretch(1)
        mic_card.body().addWidget(mic_buttons)

        self.combo_device = QComboBox()
        self.combo_device.addItem("Устройство по умолчанию", None)
        for index, name in system_access.list_microphones():
            self.combo_device.addItem(name, index)
        position = self.combo_device.findData(self.cfg.get("input_device"))
        if position >= 0:
            self.combo_device.setCurrentIndex(position)
        self.combo_device.currentIndexChanged.connect(
            lambda: self._set("input_device", self.combo_device.currentData())
        )
        mic_card.add_row(
            "Устройство записи", "С какого микрофона писать голос", self.combo_device
        )
        layout.addWidget(mic_card)

        keys_card = Card("Перехват клавиатуры и права")
        self.access_dot_keys = StatusDot(None)
        self.access_label_keys = QLabel("Проверка перехвата клавиш…")
        self._row_with_dot(keys_card, self.access_dot_keys, self.access_label_keys)
        self.access_dot_admin = StatusDot(None)
        self.access_label_admin = QLabel("Права администратора: проверка…")
        self._row_with_dot(keys_card, self.access_dot_admin, self.access_label_admin)

        admin_button = QPushButton("Перезапустить от имени администратора")
        admin_button.clicked.connect(self._restart_admin)
        keys_card.body().addWidget(admin_button)
        hint = QLabel(
            "Админ-права нужны только для приложений, запущенных от администратора — "
            "в обычных чатах и браузере всё работает без них."
        )
        hint.setObjectName("rowHint")
        hint.setWordWrap(True)
        keys_card.body().addWidget(hint)
        layout.addWidget(keys_card)

        other_card = Card("Другие разрешения Windows")
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        for label, page_key in (
            ("Конфиденциальность", "privacy"),
            ("Автозагрузка приложений", "startup"),
            ("Уведомления", "notifications"),
        ):
            button = QPushButton(label)
            button.clicked.connect(
                lambda _checked=False, key=page_key: system_access.open_windows_settings(key)
            )
            row_layout.addWidget(button)
        row_layout.addStretch(1)
        other_card.body().addWidget(row)
        layout.addWidget(other_card)

        layout.addStretch(1)
        return page

    def _restart_admin(self) -> None:
        if system_access.restart_as_admin():
            self.request_quit.emit()
        else:
            self.set_status("Не удалось перезапустить с правами администратора")

    def refresh_access(self) -> None:
        """Перепроверяет доступы Windows и обновляет индикаторы."""
        allowed = system_access.microphone_allowed()
        works = system_access.microphone_works()
        mic_ok = True if works else (False if allowed is False else None)
        if works:
            mic_text = "Микрофон: доступ разрешён, запись работает"
        elif allowed is False:
            mic_text = "Микрофон: доступ запрещён в параметрах Windows"
        else:
            mic_text = "Микрофон: не удалось открыть запись — проверь устройство"
        self.dot_mic.set_state(mic_ok)
        self.label_mic.setText(mic_text)
        self.access_dot_mic.set_state(mic_ok)
        self.access_label_mic.setText(mic_text)

        keys_ok = system_access.keyboard_hook_available()
        keys_text = (
            "Перехват клавиш: работает"
            if keys_ok
            else "Перехват клавиш: нет доступа — нужен запуск от администратора"
        )
        self.dot_keys.set_state(keys_ok)
        self.label_keys.setText(keys_text)
        self.access_dot_keys.set_state(keys_ok)
        self.access_label_keys.setText(keys_text)

        admin = system_access.is_admin()
        self.access_dot_admin.set_state(True if admin else None)
        self.access_label_admin.setText(
            "Права администратора: есть"
            if admin
            else "Права администратора: нет (обычно не нужны)"
        )

        self.toggle_autostart.setChecked(system_access.autostart_enabled())

    # -- Система ----------------------------------------------
    def _page_system(self) -> QWidget:
        page, layout = self._page_shell(
            "Система", "Автозапуск, трей и файлы программы."
        )

        card = Card("Запуск")
        self.toggle_autostart = ToggleSwitch(system_access.autostart_enabled())
        self.toggle_autostart.toggled.connect(self._change_autostart)
        card.add_row(
            "Запускать вместе с Windows",
            "VoiceM будет включаться сразу при включении компьютера",
            self.toggle_autostart,
        )
        self.toggle_minimized = ToggleSwitch(bool(self.cfg.get("start_minimized", False)))
        self.toggle_minimized.toggled.connect(lambda v: self._set("start_minimized", v))
        card.add_row(
            "Запускаться свёрнутым",
            "При старте окно не показывать, сразу уйти в трей",
            self.toggle_minimized,
        )
        self.toggle_close_tray = ToggleSwitch(bool(self.cfg.get("close_to_tray", True)))
        self.toggle_close_tray.toggled.connect(lambda v: self._set("close_to_tray", v))
        card.add_row(
            "Крестик сворачивает в трей",
            "Программа продолжает слушать горячую клавишу",
            self.toggle_close_tray,
        )
        layout.addWidget(card)

        files_card = Card("Файлы и логи")
        files_row = QWidget()
        files_layout = QHBoxLayout(files_row)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(10)
        open_folder = QPushButton("Папка настроек")
        open_folder.clicked.connect(lambda: system_access.open_path(str(app_data_dir())))
        files_layout.addWidget(open_folder)
        open_cfg = QPushButton("Файл config.json")
        open_cfg.clicked.connect(lambda: system_access.open_path(str(config_path())))
        files_layout.addWidget(open_cfg)
        open_log = QPushButton("Журнал ошибок")
        open_log.clicked.connect(lambda: system_access.open_path(str(log_path())))
        files_layout.addWidget(open_log)
        files_layout.addStretch(1)
        files_card.body().addWidget(files_row)
        layout.addWidget(files_card)

        layout.addStretch(1)
        return page

    def _change_autostart(self, enabled: bool) -> None:
        ok = system_access.set_autostart(bool(enabled))
        self.cfg["autostart"] = bool(enabled)
        save_config(self.cfg)
        if not ok:
            self.set_status("Не удалось изменить автозапуск")
            return
        self.set_status("Автозапуск включён" if enabled else "Автозапуск выключен")

    # -- История ----------------------------------------------
    def _page_history(self) -> QWidget:
        page, layout = self._page_shell(
            "История", "Последние распознанные фразы. Двойной клик — скопировать."
        )

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._copy_history_item)
        layout.addWidget(self.history_list, 1)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        clear_button = QPushButton("Очистить")
        clear_button.clicked.connect(self.history_list.clear)
        row_layout.addWidget(clear_button)
        self.toggle_history = ToggleSwitch(bool(self.cfg.get("keep_history", True)))
        self.toggle_history.toggled.connect(lambda v: self._set("keep_history", v))
        keep_label = QLabel("Сохранять историю в памяти")
        keep_label.setObjectName("rowTitle")
        row_layout.addStretch(1)
        row_layout.addWidget(keep_label)
        row_layout.addWidget(self.toggle_history)
        layout.addWidget(row)
        return page

    def _copy_history_item(self, item) -> None:  # noqa: ANN001
        try:
            from PySide6.QtGui import QGuiApplication

            text = item.text()
            if "  —  " in text:
                text = text.split("  —  ", 1)[1]
            QGuiApplication.clipboard().setText(text)
            self.set_status("Скопировано в буфер")
        except Exception:
            pass

    def add_history(self, text: str) -> None:
        if not bool(self.cfg.get("keep_history", True)):
            return
        stamp = datetime.now().strftime("%H:%M")
        self.history_list.insertItem(0, f"{stamp}  —  {text}")
        while self.history_list.count() > 100:
            self.history_list.takeItem(self.history_list.count() - 1)

    # -- О программе ------------------------------------------
    def _page_about(self) -> QWidget:
        page, layout = self._page_shell("О программе", "VoiceM 1.1.0")

        card = Card("VoiceM")
        text = QLabel(
            "Голосовой ввод в любое поле ввода Windows.\n\n"
            "• Распознавание речи полностью локальное — интернет не нужен\n"
            "• Модель faster-whisper вшита в установщик\n"
            "• Слова-паразиты и заикания убираются автоматически\n"
            "• Лицензия MIT"
        )
        text.setObjectName("rowHint")
        text.setWordWrap(True)
        card.body().addWidget(text)
        layout.addWidget(card)

        model_card = Card("Модель")
        self.about_model = QLabel("Проверка модели…")
        self.about_model.setObjectName("rowTitle")
        self.about_model.setWordWrap(True)
        model_card.body().addWidget(self.about_model)
        layout.addWidget(model_card)

        layout.addStretch(1)
        return page

    # -- внешние слоты -------------------------------------
    def set_status(self, text: str) -> None:
        self.top_status.setText(text)

    def set_model_state(self, ok: bool, message: str) -> None:
        self.dot_model.set_state(True if ok else False)
        self.label_model.setText(message)
        self.about_model.setText(message)

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if bool(self.cfg.get("close_to_tray", True)):
            event.ignore()
            self.hide()
        else:
            event.accept()
            self.request_quit.emit()
