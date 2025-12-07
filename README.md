# AI YouTube Project (PyTorch + PyQt5)

This app demonstrates a simple desktop GUI that plays YouTube videos and periodically runs a PyTorch model on captured frames to display basic insights.

## Stack
- PyTorch (`torch`, `torchvision`) for inference (ResNet18 pretrained on ImageNet)
- PyQt5 for the GUI
- PyQtWebEngine (`pyqtwebengine`) to embed a YouTube page in-app
- Optional: Selenium + webdriver-manager to control an external browser

## Quickstart
1. Create a virtual environment (recommended) and install dependencies:
   - `python -m venv .venv && .venv\Scripts\activate` (Windows)
   - `pip install --upgrade pip`
   - `pip install -r requirements.txt`
2. Run the app:
   - `python main.py`
3. Paste a YouTube URL and click `Load`. Use `Play/Pause/Next` to control playback. The model output appears at the bottom.

Notes:
- On first run, torchvision downloads pretrained weights (requires internet).
- If you see a message about PyQtWebEngine, install the extra package or keep using an external browser via Selenium.

## Project Structure
```
assets/                 # Media assets (optional)
 gui/
   main_window.py       # PyQt5 main window with web player + AI overlay
 models/
   ai_model.py          # PyTorch inference wrapper (ResNet18)
 scripts/
   selenium_control.py  # Optional Selenium controller stub
 main.py                # Entry point
 requirements.txt       # Dependencies (PyTorch + PyQt5)
 README.md              # This file
```

## Selenium (Optional)
If you prefer controlling an external browser:
- `from scripts.selenium_control import YouTubeController`
- Use `ctrl = YouTubeController(); ctrl.open(url); ctrl.play(); ctrl.pause(); ctrl.next()`

WebDriver is auto-managed by `webdriver-manager` for Chrome.

## Troubleshooting
- Black/blank captures from the embedded video can happen due to GPU/driver composition. If so, reduce capture interval, resize the window, or fall back to Selenium + screen capture strategies.
- If `torchvision` model download fails, ensure network access or manually provide weights.
- If `pyqtwebengine` import fails, install `pyqtwebengine` and try again.
