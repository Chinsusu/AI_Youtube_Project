import argparse
from gui.main_window import run_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI YouTube (PyTorch + PyQt5)")
    parser.add_argument("--auto-close-ms", type=int, default=None, help="Auto close after N milliseconds")
    args = parser.parse_args()
    run_app(auto_close_ms=args.auto_close_ms)
