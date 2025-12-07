from typing import Optional

import numpy as np

from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    QWebEngineView = None  # type: ignore

try:
    from models.ai_model import AIModel  # type: ignore
except Exception:  # pragma: no cover
    AIModel = None  # type: ignore


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI YouTube (PyTorch + PyQt5)")
        self.resize(1200, 800)

        self.model = None
        try:
            if AIModel is not None:
                self.model = AIModel()
        except Exception:
            # Graceful degradation if PyTorch/torchvision is unavailable
            self.model = None
        self.web_view: Optional[QWebEngineView] = None

        # Top controls
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter YouTube URL...")
        self.url_input.setText("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.load_btn = QPushButton("Load")
        self.play_btn = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.next_btn = QPushButton("Next")

        controls = QHBoxLayout()
        controls.addWidget(self.url_input)
        controls.addWidget(self.load_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.next_btn)

        # Insights label
        self.insights_label = QLabel("Model: waiting for frame...")
        self.insights_label.setAlignment(Qt.AlignLeft)

        # Web view or fallback
        content: QWidget
        if QWebEngineView is not None:
            self.web_view = QWebEngineView(self)
            content = self.web_view
        else:
            fallback = QLabel(
                "PyQtWebEngine not available. Install 'pyqtwebengine' to enable in-app video."
            )
            fallback.setAlignment(Qt.AlignCenter)
            content = fallback

        # Layout
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.addLayout(controls)
        layout.addWidget(content, stretch=1)
        layout.addWidget(self.insights_label)
        self.setCentralWidget(root)

        # Connections
        self.load_btn.clicked.connect(self.load_url)
        self.play_btn.clicked.connect(self.play_video)
        self.pause_btn.clicked.connect(self.pause_video)
        self.next_btn.clicked.connect(self.next_video)

        # Periodic capture + inference
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.capture_and_analyze)
        self.timer.start()

        # Initial load
        self.load_url()

    def load_url(self) -> None:
        url = self.url_input.text().strip()
        if self.web_view is not None and url:
            self.web_view.setUrl(QUrl(url))

    def run_js(self, script: str) -> None:
        if self.web_view is not None:
            page = self.web_view.page()
            page.runJavaScript(script)

    def play_video(self) -> None:
        # Try to play the HTML5 video element (works on many YouTube pages)
        self.run_js("(document.querySelector('video')||{}).play && document.querySelector('video').play();")

    def pause_video(self) -> None:
        self.run_js("(document.querySelector('video')||{}).pause && document.querySelector('video').pause();")

    def next_video(self) -> None:
        # Try typical next-button selectors used by YouTube's player
        self.run_js(
            "var b=document.querySelector('.ytp-next-button, a[aria-label^=\\'Next\\']'); if(b){b.click()}"
        )

    def _grab_web_view_as_bgr(self) -> Optional[np.ndarray]:
        if self.web_view is None:
            return None
        pixmap: QPixmap = self.web_view.grab()
        if pixmap.isNull():
            return None
        image = pixmap.toImage().convertToFormat(4)  # QImage::Format_RGBA8888
        width = image.width()
        height = image.height()
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
        # RGBA -> BGR drop alpha
        bgr = arr[:, :, :3][:, :, ::-1]
        return bgr

    def capture_and_analyze(self) -> None:
        try:
            if self.model is None:
                self.insights_label.setText("Model unavailable: PyTorch/weights not installed")
                return
            frame_bgr = self._grab_web_view_as_bgr()
            if frame_bgr is None:
                self.insights_label.setText("Model: no frame available")
                return
            label, prob = self.model.predict(frame_bgr)
            self.insights_label.setText(f"Model: {label} ({prob:.2%})")
        except Exception as exc:
            self.insights_label.setText(f"Model error: {exc}")


def run_app(auto_close_ms: int | None = None) -> None:
    import sys
    from PyQt5.QtCore import QTimer

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    if auto_close_ms and auto_close_ms > 0:
        QTimer.singleShot(auto_close_ms, app.quit)
    sys.exit(app.exec_())
