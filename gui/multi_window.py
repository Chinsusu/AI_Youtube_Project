from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
)

from scripts.selenium_control import YouTubeController
from pathlib import Path
import uuid
import re
import json


class SessionItemWidget(QWidget):
    def __init__(self, url: str = "", default_skip: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ctrl: Optional[YouTubeController] = None
        self._is_playing_cache: bool = False

        self.url_edit = QLineEdit(self)
        self.url_edit.setPlaceholderText("YouTube URL...")
        self.url_edit.setText(url)
        self.proxy_edit = QLineEdit(self)
        self.proxy_edit.setPlaceholderText("proxy e.g. host:port or socks5://host:port")
        self.proxy_edit.setFixedWidth(230)
        self.profile_edit = QLineEdit(self)
        self.profile_edit.setPlaceholderText("profile name (folder)")
        self.profile_edit.setFixedWidth(150)

        self.open_btn = QPushButton("Open", self)
        self.toggle_btn = QPushButton("Play", self)
        self.next_btn = QPushButton("Next", self)
        self.close_btn = QPushButton("Close", self)
        self.skip_cb = QCheckBox("Skip ads", self)
        self.skip_cb.setChecked(default_skip)
        self.title_label = QLabel("-", self)
        self.title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 3, 6, 3)
        row.addWidget(self.url_edit, stretch=1)
        row.addWidget(self.proxy_edit)
        row.addWidget(self.profile_edit)
        row.addWidget(self.open_btn)
        row.addWidget(self.toggle_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.close_btn)
        row.addWidget(self.skip_cb)
        row.addWidget(self.title_label, stretch=1)

        self.open_btn.clicked.connect(self.open)
        self.toggle_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.next)
        self.close_btn.clicked.connect(self.stop)

        # Periodically refresh title if controller is active
        self.title_timer = QTimer(self)
        self.title_timer.setInterval(1500)
        self.title_timer.timeout.connect(self.refresh_title)

    def ensure_ctrl(self) -> None:
        if self.ctrl is None:
            self.ctrl = YouTubeController()
            # Start only when opening a URL

    def open(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        self.ensure_ctrl()
        assert self.ctrl is not None
        try:
            proxy = self.proxy_edit.text().strip() or None
            # Resolve profile directory (base: profiles/<safe-name>)
            name = (self.profile_edit.text() or '').strip()
            if not name:
                name = f"profile-{uuid.uuid4().hex[:8]}"
                self.profile_edit.setText(name)
            safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name)
            base = Path(__file__).resolve().parent.parent / 'profiles'
            base.mkdir(exist_ok=True)
            profile_dir = str(base / safe)
            self.ctrl.open(url, proxy=proxy, profile_dir=profile_dir)
            self.title_timer.start()
            self.refresh_title()
            self.update_toggle_text()
        except Exception as e:
            self.title_label.setText(f"Open failed: {e}")

    def toggle_play_pause(self) -> None:
        if not self.ctrl:
            return
        try:
            now_playing = self.ctrl.toggle_play_pause()
            self._is_playing_cache = now_playing
            self.update_toggle_text()
        except Exception:
            pass

    def next(self) -> None:
        if not self.ctrl:
            return
        try:
            self.ctrl.next()
        except Exception:
            pass

    def stop(self) -> None:
        try:
            if self.ctrl:
                self.ctrl.stop()
                self.ctrl = None
        except Exception:
            self.ctrl = None
        self.title_timer.stop()

    def refresh_title(self) -> None:
        if not self.ctrl:
            self.title_label.setText("-")
            return
        try:
            title = self.ctrl.get_title().strip() or "-"
            self.title_label.setText(title)
            self.update_toggle_text()
        except Exception:
            pass

    def update_toggle_text(self) -> None:
        try:
            if not self.ctrl:
                self.toggle_btn.setText("Play")
                return
            # Prefer querying real state; fall back to cache
            try:
                self._is_playing_cache = self.ctrl.is_playing()
            except Exception:
                pass
            self.toggle_btn.setText("Pause" if self._is_playing_cache else "Play")
        except Exception:
            pass

    def tick_maintenance(self) -> None:
        if self.ctrl:
            # Error detection + recovery (throttled internally)
            try:
                self.ctrl.error_recover_tick()
            except Exception:
                pass
            # Ad skipping if enabled
            if self.skip_cb.isChecked():
                try:
                    self.ctrl.skip_ads_tick()
                except Exception:
                    pass


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI YouTube Controller (PyQt5 + Selenium)")
        self.resize(1000, 640)
        # Keep strong references to row widgets to avoid Python GC breaking signals
        self._session_widgets: List[SessionItemWidget] = []

        # Top controls
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL...")
        self.import_btn = QPushButton("Import List", self)
        self.save_btn = QPushButton("Save Sessions", self)
        self.load_btn = QPushButton("Load Sessions", self)
        self.open_btn = QPushButton("Open", self)
        self.global_skip_cb = QCheckBox("Auto-skip ads (default)", self)
        self.global_skip_cb.setChecked(True)
        self.threads_label = QLabel("Threads:", self)
        self.threads_spin = QSpinBox(self)
        self.threads_spin.setRange(1, 50)
        self.threads_spin.setValue(2)

        top = QHBoxLayout()
        top.addWidget(self.url_input, stretch=1)
        top.addWidget(self.import_btn)
        top.addWidget(self.save_btn)
        top.addWidget(self.load_btn)
        top.addWidget(self.open_btn)
        top.addWidget(self.global_skip_cb)
        top.addWidget(self.threads_label)
        top.addWidget(self.threads_spin)

        # Sessions list
        self.sessions = QListWidget(self)

        # Bottom info
        self.status_label = QLabel("Ready", self)
        self.status_label.setAlignment(Qt.AlignLeft)
        self.progress_label = QLabel("Đang phát: -   0/0", self)
        self.progress_label.setAlignment(Qt.AlignRight)

        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label)
        bottom.addStretch(1)
        bottom.addWidget(self.progress_label)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.addLayout(top)
        layout.addWidget(self.sessions, stretch=1)
        layout.addLayout(bottom)
        self.setCentralWidget(root)

        # Wiring
        self.import_btn.clicked.connect(self.import_list)
        self.save_btn.clicked.connect(self.save_sessions)
        self.load_btn.clicked.connect(self.load_sessions)
        self.open_btn.clicked.connect(self.open_from_input)
        self.sessions.currentRowChanged.connect(lambda _row: self.update_progress())

        # Timers
        self.ads_timer = QTimer(self)
        self.ads_timer.setInterval(800)
        self.ads_timer.timeout.connect(self._tick_all_ads)
        self.ads_timer.start()

        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1500)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start()

        self.update_progress()

    # Helpers
    def _add_session_widget(self, url: str = "") -> SessionItemWidget:
        w = SessionItemWidget(url=url, default_skip=self.global_skip_cb.isChecked())
        it = QListWidgetItem(self.sessions)
        it.setSizeHint(w.sizeHint())
        self.sessions.addItem(it)
        self.sessions.setItemWidget(it, w)
        # Keep a Python reference so signals/slots remain alive
        self._session_widgets.append(w)
        return w


    def _selected_widget(self) -> Optional[SessionItemWidget]:
        row = self.sessions.currentRow()
        if row < 0:
            return None
        item = self.sessions.item(row)
        if not item:
            return None
        w = self.sessions.itemWidget(item)
        return w  # type: ignore

    # Actions
    def import_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open URL List", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        added = 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if not url or url.startswith("#"):
                        continue
                    self._add_session_widget(url)
                    added += 1
            self.status_label.setText(f"Imported {added} URLs from {path}")
        except Exception as e:
            self.status_label.setText(f"Import failed: {e}")
        self.update_progress()

    def open_from_input(self) -> None:
        threads = int(self.threads_spin.value())
        url = self.url_input.text().strip()
        opened = 0
        if url:
            # Open N new sessions with the same URL
            for _ in range(threads):
                w = self._add_session_widget(url)
                self.sessions.setCurrentRow(self.sessions.count() - 1)
                w.open()
                opened += 1
            self.url_input.clear()
            self.status_label.setText(f"Opened {opened} new session(s)")
            self.update_progress()
            return

        # No URL typed: open up to N unopened existing sessions (rows without driver)
        for i in range(self.sessions.count()):
            if opened >= threads:
                break
            item = self.sessions.item(i)
            if not item:
                continue
            w = self.sessions.itemWidget(item)
            if not isinstance(w, SessionItemWidget):
                continue
            if w.ctrl is None:
                self.sessions.setCurrentRow(i)
                w.open()
                opened += 1
        self.status_label.setText(f"Opened {opened} existing session(s)")
        self.update_progress()

    def _tick_all_ads(self) -> None:
        # Iterate all sessions and tick skip-ads where enabled
        try:
            for i in range(self.sessions.count()):
                item = self.sessions.item(i)
                if not item:
                    continue
                w = self.sessions.itemWidget(item)
                if not isinstance(w, SessionItemWidget):
                    continue
                w.tick_maintenance()
        except Exception:
            pass

    def update_progress(self) -> None:
        total = self.sessions.count()
        current_index = self.sessions.currentRow()
        pos = (current_index + 1) if current_index >= 0 else 0
        title = "-"
        try:
            w = self._selected_widget()
            if isinstance(w, SessionItemWidget):
                title = w.title_label.text().strip() or "-"
        except Exception:
            pass
        self.progress_label.setText(f"Đang phát: {title}   {pos}/{total}")

    # Save/Load sessions (URL, proxy, profile) to JSON
    def save_sessions(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Sessions", "sessions.json", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        data = []
        for i in range(self.sessions.count()):
            item = self.sessions.item(i)
            if not item:
                continue
            w = self.sessions.itemWidget(item)
            if not isinstance(w, SessionItemWidget):
                continue
            data.append({
                'url': w.url_edit.text().strip(),
                'proxy': w.proxy_edit.text().strip(),
                'profile': w.profile_edit.text().strip(),
            })
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'sessions': data}, f, ensure_ascii=False, indent=2)
            self.status_label.setText(f"Saved {len(data)} sessions to {path}")
        except Exception as e:
            self.status_label.setText(f"Save failed: {e}")

    def load_sessions(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Sessions", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                obj = json.load(f)
            items = obj.get('sessions') or []
            added = 0
            for s in items:
                url = (s.get('url') or '').strip()
                proxy = (s.get('proxy') or '').strip()
                profile = (s.get('profile') or '').strip()
                w = self._add_session_widget(url)
                if proxy:
                    w.proxy_edit.setText(proxy)
                if profile:
                    w.profile_edit.setText(profile)
                added += 1
            self.status_label.setText(f"Loaded {added} sessions from {path}")
            self.update_progress()
        except Exception as e:
            self.status_label.setText(f"Load failed: {e}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        # Cleanly stop all sessions
        try:
            for w in self._session_widgets:
                try:
                    w.stop()
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)


def run_app(auto_close_ms: int | None = None) -> None:
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    if auto_close_ms and auto_close_ms > 0:
        QTimer.singleShot(auto_close_ms, app.quit)  # type: ignore[name-defined]
    sys.exit(app.exec_())
