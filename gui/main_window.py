from typing import Optional

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
    QFileDialog,
)

from scripts.selenium_control import YouTubeController
import random


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI YouTube Controller (PyQt5 + Selenium)")
        self.resize(900, 600)

        self.ctrl = YouTubeController()

        # Controls
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL...")
        self.import_btn = QPushButton("Import List")
        self.open_btn = QPushButton("Open")
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.next_btn = QPushButton("Next")
        self.auto_skip_cb = QCheckBox("Auto-skip ads")
        self.auto_skip_cb.setChecked(True)

        controls = QHBoxLayout()
        controls.addWidget(self.url_input)
        controls.addWidget(self.import_btn)
        controls.addWidget(self.open_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.auto_skip_cb)

        # List of URLs
        self.list_widget = QListWidget(self)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.progress_label = QLabel("0/0")
        self.progress_label.setAlignment(Qt.AlignRight)

        # Layout
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.addLayout(controls)
        layout.addWidget(self.list_widget, stretch=1)
        info = QHBoxLayout()
        info.addWidget(self.status_label)
        info.addStretch(1)
        info.addWidget(self.progress_label)
        layout.addLayout(info)
        self.setCentralWidget(root)

        # Connections
        self.import_btn.clicked.connect(self.import_list)
        self.open_btn.clicked.connect(self.open_current)
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.next_btn.clicked.connect(self.next_video)
        self.list_widget.itemDoubleClicked.connect(self._open_item)

        # Auto-skip ads tick
        self.ad_timer = QTimer(self)
        self.ad_timer.setInterval(700)
        self.ad_timer.timeout.connect(self._attempt_skip_ads)
        if self.auto_skip_cb.isChecked():
            self.ad_timer.start()
        self.auto_skip_cb.toggled.connect(self._on_auto_skip_toggled)

        # Shuffle play order state
        self.play_order: list[int] = []
        self.play_pos: int = -1
        self._update_progress()

    def import_list(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open URL List", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith("#"):
                        self.list_widget.addItem(url)
            self._rebuild_shuffle_order()
            self._update_progress()
            self.status_label.setText(f"Loaded and shuffled list from {path}")
        except Exception as e:
            self.status_label.setText(f"Load failed: {e}")

    def _current_url(self) -> Optional[str]:
        # Prefer manual input; fall back to selected list item
        text = self.url_input.text().strip()
        if text:
            return text
        item = self.list_widget.currentItem()
        if item is not None:
            return item.text().strip()
        return None

    def open_current(self) -> None:
        url = self._current_url()
        if not url:
            self.status_label.setText("No URL selected or entered")
            return
        try:
            self.ctrl.open(url)
            # Mark opened if current list item matches the opened URL
            row = self.list_widget.currentRow()
            if row >= 0:
                item = self.list_widget.item(row)
                if item and item.text().strip() == url:
                    self._mark_opened_row(row)
                    # Align play pointer to this row if present in the shuffled order
                    try:
                        idx_in_order = self.play_order.index(row)
                        self.play_pos = idx_in_order
                    except Exception:
                        pass
            self._update_progress()
            self.status_label.setText("Opened in browser")
        except Exception as e:
            self.status_label.setText(f"Open failed: {e}")

    def _open_item(self, item) -> None:
        try:
            url = item.text().strip()
            if not url:
                self.status_label.setText("Empty item URL")
                return
            self.list_widget.setCurrentItem(item)
            self.ctrl.open(url)
            # Mark as opened
            row = self.list_widget.currentRow()
            if row >= 0:
                self._mark_opened_row(row)
                # Align play pointer to this row if present in the shuffled order
                try:
                    idx_in_order = self.play_order.index(row)
                    self.play_pos = idx_in_order
                except Exception:
                    pass
            self._update_progress()
            self.status_label.setText(f"Opened: {url}")
        except Exception as e:
            self.status_label.setText(f"Open failed: {e}")

    def _mark_opened_row(self, row: int) -> None:
        try:
            item = self.list_widget.item(row)
            if not item:
                return
            item.setData(Qt.UserRole, True)
            # Optional visual hint: dim opened entries
            try:
                from PyQt5.QtGui import QColor

                item.setForeground(QColor('#888888'))
            except Exception:
                pass
        except Exception:
            pass

    def _rebuild_shuffle_order(self) -> None:
        # Clear opened marks and rebuild a shuffled play order
        try:
            from PyQt5.QtGui import QColor
            default_color = QColor('#000000')
        except Exception:
            default_color = None  # type: ignore

        self.play_order = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if not it:
                continue
            # Reset opened state and color
            it.setData(Qt.UserRole, False)
            try:
                if default_color is not None:
                    it.setForeground(default_color)
            except Exception:
                pass
            url = it.text().strip()
            if url:
                self.play_order.append(i)

        random.shuffle(self.play_order)
        self.play_pos = -1
        self._update_progress()

    def _update_progress(self) -> None:
        try:
            total = len(self.play_order)
            if total <= 0:
                self.progress_label.setText("0/0")
                return
            pos = self.play_pos + 1 if 0 <= self.play_pos < total else 0
            self.progress_label.setText(f"{pos}/{total}")
        except Exception:
            # Keep previous text on any error
            pass

    def play_video(self) -> None:
        try:
            self.ctrl.play()
            self.status_label.setText("Play")
        except Exception as e:
            self.status_label.setText(f"Play failed: {e}")

    def pause_video(self) -> None:
        try:
            self.ctrl.pause()
            self.status_label.setText("Pause")
        except Exception as e:
            self.status_label.setText(f"Pause failed: {e}")

    def next_video(self) -> None:
        try:
            if self.list_widget.count() == 0:
                self.status_label.setText("List is empty")
                return
            # Ensure we have a valid shuffled order
            if not self.play_order or any(i >= self.list_widget.count() for i in self.play_order):
                self._rebuild_shuffle_order()

            # Advance pointer; reshuffle and loop when reaching the end
            self.play_pos += 1
            if self.play_pos >= len(self.play_order):
                self._rebuild_shuffle_order()
                if not self.play_order:
                    self.status_label.setText("No valid URLs to play")
                    return
                self.play_pos = 0

            row = self.play_order[self.play_pos]
            self.list_widget.setCurrentRow(row)
            it = self.list_widget.item(row)
            if not it:
                self.status_label.setText("No valid item")
                return
            url = it.text().strip()
            if not url:
                self.status_label.setText("Empty URL at selected item")
                return
            self.ctrl.open(url)
            self._mark_opened_row(row)
            self._update_progress()
            self.status_label.setText(f"Opened: {url}")
        except Exception as e:
            self.status_label.setText(f"Next failed: {e}")

    def _attempt_skip_ads(self) -> None:
        if not self.auto_skip_cb.isChecked():
            return
        try:
            self.ctrl.skip_ads_tick()
        except Exception:
            pass

    def _on_auto_skip_toggled(self, checked: bool) -> None:
        try:
            if checked:
                if not self.ad_timer.isActive():
                    self.ad_timer.start()
            else:
                if self.ad_timer.isActive():
                    self.ad_timer.stop()
                # Best-effort restore
                try:
                    self.ctrl.exec_js("var v=document.querySelector('video'); if(v){ try{ v.playbackRate=1.0; }catch(e){} }")
                except Exception:
                    pass
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.ctrl.stop()
        except Exception:
            pass
        super().closeEvent(event)


def run_app(auto_close_ms: int | None = None) -> None:
    import sys
    from PyQt5.QtCore import QTimer

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    if auto_close_ms and auto_close_ms > 0:
        QTimer.singleShot(auto_close_ms, app.quit)
    sys.exit(app.exec_())
