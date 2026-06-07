"""Screenshot capture for the ROK PC game window."""

from ctypes import windll
from typing import Optional

import cv2
import numpy as np
import win32gui
import win32ui
from loguru import logger

from rokbot.pc_controller.window_manager import WindowManager


class WindowCapture:
    """Captures screenshots of the game window."""

    def __init__(self, window_manager: WindowManager):
        self.window_manager = window_manager

    def capture(self) -> Optional[np.ndarray]:
        """Capture the game client area and return as BGR numpy array.

        Uses PrintWindow so the window contents are captured even when
        overlapped by other applications.
        """
        if not self.window_manager.is_window_valid():
            logger.error("Cannot capture: game window not found")
            return None

        rect = self.window_manager.get_client_rect()
        if rect is None:
            return None

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        hwnd = self.window_manager.hwnd
        hwndDC = None
        mfcDC = None
        saveDC = None
        saveBitMap = None

        try:
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # PrintWindow with PW_RENDERFULLCONTENT (3) captures even when occluded
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
            if result == 0:
                # Fallback to BitBlt if PrintWindow fails
                saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), 13369376)  # SRCCOPY

            # Convert bitmap to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            image = np.frombuffer(bmpstr, dtype=np.uint8)
            image.shape = (height, width, 4)  # BGRA
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            logger.debug(f"Window captured (PrintWindow): {image.shape}")
            return image
        except Exception as e:
            logger.error(f"Window capture failed: {e}")
            return None
        finally:
            try:
                if saveBitMap is not None:
                    win32gui.DeleteObject(saveBitMap.GetHandle())
                if saveDC is not None:
                    saveDC.DeleteDC()
                if mfcDC is not None:
                    mfcDC.DeleteDC()
                if hwndDC is not None:
                    win32gui.ReleaseDC(hwnd, hwndDC)
            except Exception:
                pass

    def save_screenshot(self, path: str) -> bool:
        """Capture and save to disk."""
        image = self.capture()
        if image is None:
            return False
        cv2.imwrite(path, image)
        logger.info(f"Screenshot saved to {path}")
        return True
