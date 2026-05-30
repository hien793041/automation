"""List all visible windows to help identify the game window title.

Usage:
    python scripts/list_windows.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import win32gui


def main():
    print("=" * 60)
    print("Visible Windows")
    print("=" * 60)
    print(f"{'HWND':<10} {'Class Name':<30} {'Window Title'}")
    print("-" * 60)

    def callback(hwnd, _extra):
        if win32gui.IsWindowVisible(hwnd):
            try:
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if title:
                    print(f"{hwnd:<10} {class_name:<30} {title}")
            except Exception:
                pass
        return True

    win32gui.EnumWindows(callback, None)
    print("=" * 60)
    print("\nLook for your game window title and update config/bot.yaml")
    print("  pc:\n    window_title: \"Exact Title Here\"")


if __name__ == "__main__":
    main()
