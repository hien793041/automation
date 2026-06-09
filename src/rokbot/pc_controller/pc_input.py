"""Mouse/keyboard input for the ROK PC game window."""

import time
from typing import Optional, Tuple

import pyautogui
from loguru import logger

from rokbot.pc_controller.window_manager import WindowManager


class PCInput:
    """Execute clicks and key presses on the game window.

    Supports optional humanization (anti-detection) via TimingEngine,
    MovementEngine, DecisionEngine and ErrorSimulator.
    """

    def __init__(
        self,
        window_manager: WindowManager,
        humanization_config=None,
    ):
        self.window_manager = window_manager
        pyautogui.FAILSAFE = True  # move mouse to screen corner to abort
        pyautogui.PAUSE = 0.05

        self._humanization_config = humanization_config
        self._timing = None
        self._movement = None
        self._decision = None
        self._error_sim = None

        if humanization_config and getattr(humanization_config, "enabled", False):
            from rokbot.humanization.timing_engine import TimingEngine
            from rokbot.humanization.movement_engine import MovementEngine
            from rokbot.humanization.decision_engine import DecisionEngine
            from rokbot.humanization.error_simulator import ErrorSimulator

            self._timing = TimingEngine(
                profile_path=getattr(humanization_config, "profile_path", None)
            )
            self._movement = MovementEngine()
            self._decision = DecisionEngine(
                fatigue_half_life_hours=getattr(humanization_config, "fatigue_half_life_hours", 2.0),
                base_distraction_rate=getattr(humanization_config, "base_distraction_rate", 0.08),
                base_misclick_rate=getattr(humanization_config, "base_misclick_rate", 0.01),
            )
            self._error_sim = ErrorSimulator(self._decision)
            logger.info("Humanization enabled for PCInput")

    def _human_delay(self, distribution: str = "reaction_time", min_seconds: float = 0.01) -> None:
        """Sleep using humanized timing if enabled."""
        if self._timing:
            delay_ms = self._timing.sample(distribution)
            time.sleep(max(min_seconds, delay_ms / 1000.0))

    def tap(self, x: int, y: int) -> None:
        """Click at coordinates relative to the game window client area."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            logger.error("Cannot tap: game window not found")
            return

        left, top, _, _ = rect
        abs_x = left + x
        abs_y = top + y

        if self._error_sim:
            abs_x, abs_y = self._error_sim.maybe_misclick((abs_x, abs_y))

        if self._timing:
            self._human_delay("reaction_time")

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

        if self._movement:
            path = self._movement.generate_path((x1, y1), (x2, y2))
            if len(path) > 1:
                pyautogui.moveTo(path[0][0], path[0][1])
                pyautogui.mouseDown()
                for px, py in path[1:]:
                    pyautogui.moveTo(px, py)
                pyautogui.mouseUp()
                logger.debug(f"PC swipe humanized ({start}) -> ({end})")
                return

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

    def type_text(self, text: str, interval: float = 0.01) -> None:
        """Type text into the game window."""
        pyautogui.typewrite(text, interval=interval)
        logger.debug(f"Typed text: '{text}'")

    def press_key(self, key: str) -> None:
        """Press and release a keyboard key immediately (one tap)."""
        pyautogui.press(key)
        logger.debug(f"Pressed key '{key}'")

    def hold_key(self, key: str, duration: float) -> None:
        """Hold a keyboard key for a given duration."""
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
        logger.debug(f"Held key '{key}' for {duration:.2f}s")

    def hold_key_native(self, key: str, duration: float) -> None:
        """Hold a keyboard key using win32api.keybd_event (bypasses some anti-bot blocks)."""
        import win32api
        import win32con

        VK_MAP = {
            "up": win32con.VK_UP,
            "down": win32con.VK_DOWN,
            "left": win32con.VK_LEFT,
            "right": win32con.VK_RIGHT,
            "esc": win32con.VK_ESCAPE,
        }
        vk = VK_MAP.get(key.lower())
        if vk is None:
            logger.warning(f"hold_key_native: unsupported key '{key}', falling back to hold_key")
            self.hold_key(key, duration)
            return

        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(duration)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        logger.debug(f"Held key '{key}' for {duration:.2f}s (native)")

    def move_to_safe_zone(self) -> None:
        """Move mouse to a safe corner to avoid covering UI elements during capture."""
        rect = self.window_manager.get_client_rect()
        if rect is None:
            return
        left, top, _, _ = rect
        pyautogui.moveTo(left + 10, top + 10)
        logger.debug("Moved mouse to safe zone (10, 10)")
