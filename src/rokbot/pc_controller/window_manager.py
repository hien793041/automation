"""Find and track the ROK PC game window."""

import ctypes
from typing import Optional, Tuple

import win32gui
from loguru import logger

# Make process DPI-aware so win32gui, ImageGrab and pyautogui agree on physical pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PerMonitorV2
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class WindowManager:
    """Manages the game window handle and geometry."""

    def __init__(self, window_title_substring: str = "Rise of Kingdoms"):
        self.window_title_substring = window_title_substring
        self.hwnd: Optional[int] = None
        self._find_window()

    def _find_window(self) -> None:
        """Enumerate windows to locate the game window."""
        self.hwnd = None

        # Window classes to ignore (File Explorer, browsers, etc.)
        IGNORED_CLASSES = {"CabinetWClass", "ExploreWClass"}

        def callback(hwnd: int, _extra) -> bool:
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                try:
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name in IGNORED_CLASSES:
                        return True
                except Exception:
                    pass

                title = win32gui.GetWindowText(hwnd)
                if self.window_title_substring.lower() in title.lower():
                    self.hwnd = hwnd
                    logger.info(f"Found game window: '{title}' (hwnd={hwnd})")
                    return False  # stop enumeration
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception as e:
            logger.warning(f"EnumWindows error: {e}")

        if self.hwnd is None:
            logger.warning(
                f"Game window not found (looking for '{self.window_title_substring}')"
            )

    def is_window_valid(self) -> bool:
        """Return True if the tracked window still exists."""
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            return True
        self._find_window()
        return self.hwnd is not None

    def get_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Return (left, top, right, bottom) of the full window."""
        if not self.is_window_valid():
            return None
        return win32gui.GetWindowRect(self.hwnd)

    def get_client_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Return (left, top, right, bottom) of the client area."""
        if not self.is_window_valid():
            return None
        rect = win32gui.GetClientRect(self.hwnd)
        left, top = win32gui.ClientToScreen(self.hwnd, (rect[0], rect[1]))
        right, bottom = win32gui.ClientToScreen(self.hwnd, (rect[2], rect[3]))
        return left, top, right, bottom

    def get_client_size(self) -> Optional[Tuple[int, int]]:
        """Return (width, height) of the client area."""
        rect = self.get_client_rect()
        if rect is None:
            return None
        left, top, right, bottom = rect
        return right - left, bottom - top

    def activate_window(self) -> bool:
        """Bring the game window to the foreground and return True on success.

        This is useful before sending hotkeys so the input reaches the game
        instead of whatever window is currently focused.
        """
        if not self.is_window_valid():
            return False
        try:
            # win32gui.SetForegroundWindow fails if the calling thread is not
            # foreground; use force=true via ShowWindow + SetForegroundWindow.
            import win32con

            hwnd = self.hwnd
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            logger.warning(f"Failed to activate game window: {e}")
            return False
