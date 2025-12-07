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

        # Layout
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.addLayout(controls)
        layout.addWidget(self.list_widget, stretch=1)
        layout.addWidget(self.status_label)
        self.setCentralWidget(root)

        # Connections
        self.import_btn.clicked.connect(self.import_list)
        self.open_btn.clicked.connect(self.open_current)
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.next_btn.clicked.connect(self.next_video)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.open_current())

        # Auto-skip ads tick
        self.ad_timer = QTimer(self)
        self.ad_timer.setInterval(700)
        self.ad_timer.timeout.connect(self._attempt_skip_ads)
        if self.auto_skip_cb.isChecked():
            self.ad_timer.start()
        self.auto_skip_cb.toggled.connect(self._on_auto_skip_toggled)

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
            self.status_label.setText(f"Loaded list from {path}")
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
            self.status_label.setText("Opened in browser")
        except Exception as e:
            self.status_label.setText(f"Open failed: {e}")

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
            self.ctrl.next()
            self.status_label.setText("Next")
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
