import argparse
try:
    from gui.multi_window import run_app  # new multi-session GUI
except Exception:
    from gui.main_window import run_app   # fallback to previous GUI


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI YouTube (PyTorch + PyQt5)")
    parser.add_argument("--auto-close-ms", type=int, default=None, help="Auto close after N milliseconds")
    args = parser.parse_args()
    run_app(auto_close_ms=args.auto_close_ms)
