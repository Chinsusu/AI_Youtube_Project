# AI YouTube Project (PyTorch + PyQt5)

This app provides a desktop GUI to open and control YouTube playback in a real browser (via Selenium). It supports a URL list view, manual URL entry, import from a text file, Play/Pause/Next controls, and an Auto-skip ads option.

## Stack
- PyQt5 for the GUI
- Selenium + webdriver-manager to control an external Chrome browser
- Optional: PyTorch (`torch`, `torchvision`) is included from earlier scaffolding but not required by this GUI

## Quickstart
1. Create a virtual environment (recommended) and install dependencies:
   - `python -m venv .venv && .venv\Scripts\activate` (Windows)
   - `pip install --upgrade pip`
   - `pip install -r requirements.txt`
2. Run the app:
   - `python main.py`
3. Paste a YouTube URL and click `Add` or `Open`.
   - Use `Import List` to load URLs from a `.txt` file (one per line).
   - Select an item in the list and click `Open` to launch the browser and load the link.
   - Use `Play/Pause/Next` to control playback in the opened browser. Use `Auto-skip ads` to automatically skip or accelerate ads.

Notes:
- On first run, torchvision downloads pretrained weights (requires internet).
- The GUI controls a real Chrome browser through Selenium. The first launch installs/updates a compatible ChromeDriver automatically.

## Project Structure
```
assets/                 # Media assets (optional)
 gui/
   main_window.py       # PyQt5 main window with list view + Selenium controls
 models/
   ai_model.py          # Optional PyTorch inference wrapper (legacy)
 scripts/
   selenium_control.py  # Selenium YouTube controller
 main.py                # Entry point
 requirements.txt       # Dependencies (PyTorch + PyQt5)
 README.md              # This file
```

## Selenium
The app uses Selenium to open and control Chrome. WebDriver is auto-managed by `webdriver-manager`. If Chrome is not installed or incompatible, install/update Chrome.

## Troubleshooting
- If Play/Next do not respond, ensure the YouTube tab has finished loading. The app also attempts to add `autoplay=1&mute=1` when opening.
- For Auto-skip ads, the app clicks known skip/overlay selectors and speeds ad playback; this behavior may vary if YouTube UI changes.
