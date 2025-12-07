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
    QVBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
)

from scripts.selenium_control import YouTubeController


class SessionItemWidget(QWidget):
    def __init__(self, url: str = "", default_skip: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ctrl: Optional[YouTubeController] = None

        self.url_edit = QLineEdit(self)
        self.url_edit.setPlaceholderText("YouTube URL...")
        self.url_edit.setText(url)

        self.open_btn = QPushButton("Open", self)
        self.play_btn = QPushButton("Play", self)
        self.pause_btn = QPushButton("Pause", self)
        self.next_btn = QPushButton("Next", self)
        self.close_btn = QPushButton("Close", self)
        self.skip_cb = QCheckBox("Skip ads", self)
        self.skip_cb.setChecked(default_skip)
        self.title_label = QLabel("-", self)
        self.title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row = QHBoxLayout(self)
        row.setContentsMargins(6, 3, 6, 3)
        row.addWidget(self.url_edit, stretch=1)
        row.addWidget(self.open_btn)
        row.addWidget(self.play_btn)
        row.addWidget(self.pause_btn)
        row.addWidget(self.next_btn)
        row.addWidget(self.close_btn)
        row.addWidget(self.skip_cb)
        row.addWidget(self.title_label, stretch=1)

        self.open_btn.clicked.connect(self.open)
        self.play_btn.clicked.connect(self.play)
        self.pause_btn.clicked.connect(self.pause)
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
            self.ctrl.open(url)
            self.title_timer.start()
            self.refresh_title()
        except Exception as e:
            self.title_label.setText(f"Open failed: {e}")

    def play(self) -> None:
        if not self.ctrl:
            return
        try:
            self.ctrl.play()
        except Exception:
            pass

    def pause(self) -> None:
        if not self.ctrl:
            return
        try:
            self.ctrl.pause()
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
        except Exception:
            pass

    def tick_ads(self) -> None:
        if self.ctrl and self.skip_cb.isChecked():
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
        self.open_btn = QPushButton("Open", self)
        self.global_skip_cb = QCheckBox("Auto-skip ads (default)", self)
        self.global_skip_cb.setChecked(True)

        top = QHBoxLayout()
        top.addWidget(self.url_input, stretch=1)
        top.addWidget(self.import_btn)
        top.addWidget(self.open_btn)
        top.addWidget(self.global_skip_cb)

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
        url = self.url_input.text().strip()
        if not url:
            # Try open selected row instead
            w = self._selected_widget()
            if w:
                w.open()
                self.status_label.setText("Opened selected")
            else:
                self.status_label.setText("No URL provided")
            self.update_progress()
            return
        w = self._add_session_widget(url)
        self.sessions.setCurrentRow(self.sessions.count() - 1)
        w.open()
        self.url_input.clear()
        self.status_label.setText("Opened new session")
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
                w.tick_ads()
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
