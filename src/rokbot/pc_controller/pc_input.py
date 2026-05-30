"""Mouse/keyboard input for the ROK PC game window."""

import time
from typing import Tuple

import pyautogui
from loguru import logger

from rokbot.pc_controller.window_manager import WindowManager


class PCInput:
    """Execute clicks and key presses on the game window."""

    def __init__(self, window_manager: WindowManager):
        self.window_manager = window_manager
        pyautogui.FAILSAFE = True  # move mouse to screen corner to abort
        pyautogui.PAUSE = 0.05

    def tap(self, x: int, y: int) -> None:
        """Click at coordinates relative to the game window client area."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            logger.error("Cannot tap: game window not found")
            return

        left, top, _, _ = rect
        abs_x = left + x
        abs_y = top + y

        pyautogui.click(abs_x, abs_y)
        logger.debug(f"PC tap at window ({x}, {y}) -> screen ({abs_x}, {abs_y})")

    def swipe(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: float = 0.3,
    ) -> None:
        """Drag from start to end relative to the game window."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            logger.error("Cannot swipe: game window not found")
            return

        left, top, _, _ = rect
        x1, y1 = left + start[0], top + start[1]
        x2, y2 = left + end[0], top + end[1]

        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=duration)
        logger.debug(f"PC swipe ({start}) -> ({end})")

    def key_back(self) -> None:
        """Press Escape (Android BACK equivalent on PC)."""
        pyautogui.press("esc")
        logger.debug("Pressed ESC (back)")

    def key_home(self) -> None:
        """No direct home key on PC; minimize or do nothing."""
        logger.debug("PC home key: no-op")

    def scroll(self, amount: int, x: int, y: int) -> None:
        """Scroll at window-relative coordinates."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            return
        left, top, _, _ = rect
        pyautogui.scroll(amount, left + x, top + y)
        logger.debug(f"PC scroll {amount} at ({x}, {y})")

    def move_to_safe_zone(self) -> None:
        """Move mouse to a safe corner to avoid covering UI elements during capture."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            return
        left, top, _, _ = rect
        pyautogui.moveTo(left + 10, top + 10)
        logger.debug("Moved mouse to safe zone (10, 10)")
