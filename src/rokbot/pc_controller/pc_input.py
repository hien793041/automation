"""Mouse/keyboard input for the ROK PC game window."""

import random
import time
from typing import Tuple

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
        # Disable PyAutoGUI's built-in pause; we handle all timing through
        # TimingEngine so there is no hidden fixed rhythm.
        pyautogui.PAUSE = 0.0

        self._humanization_config = humanization_config
        self._humanization_enabled = bool(
            humanization_config and getattr(humanization_config, "enabled", False)
        )
        self._timing = None
        self._movement = None
        self._decision = None
        self._error_sim = None
        self._last_safe_zone_move_time: float = 0.0

        if self._humanization_enabled:
            from rokbot.humanization.decision_engine import DecisionEngine
            from rokbot.humanization.error_simulator import ErrorSimulator
            from rokbot.humanization.movement_engine import MovementEngine
            from rokbot.humanization.timing_engine import TimingEngine

            self._timing = TimingEngine(
                profile_path=getattr(humanization_config, "profile_path", None),
                distributions=getattr(humanization_config, "timing", None),
            )
            movement_cfg = getattr(humanization_config, "movement", None) or {}
            self._movement = MovementEngine(
                fitts_a=movement_cfg.get("fitts_a", 100.0),
                fitts_b=movement_cfg.get("fitts_b", 50.0),
                control_offset_ratio=movement_cfg.get("control_offset_ratio", 0.10),
                step_ms=movement_cfg.get("step_ms", 10.0),
                jitter_sigma=movement_cfg.get("jitter_sigma", 1.5),
            )
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

    def _ensure_window_focus(self) -> bool:
        """Activate the game window before injecting input."""
        if self.window_manager is None:
            return False
        return self.window_manager.activate_window()

    def _move_humanized(
        self,
        target_x: int,
        target_y: int,
        pre_delay_distribution: str = "reaction_time",
    ) -> None:
        """Move the cursor to target screen coordinates along a human-like path."""
        if self._timing:
            self._human_delay(pre_delay_distribution)

        if self._movement is None:
            pyautogui.moveTo(target_x, target_y)
            return

        current = pyautogui.position()
        path = self._movement.generate_path((current.x, current.y), (target_x, target_y))
        if len(path) <= 1:
            pyautogui.moveTo(target_x, target_y)
            return

        step_seconds = max(0.001, self._movement.step_ms / 1000.0)
        for px, py in path:
            pyautogui.moveTo(px, py)
            time.sleep(step_seconds)

    def tap(self, x: int, y: int) -> None:
        """Click at coordinates relative to the game window client area."""
        if not self._ensure_window_focus():
            logger.error("Cannot tap: game window not available")
            return

        rect = self.window_manager.get_client_rect()
        if rect is None:
            logger.error("Cannot tap: game window not found")
            return

        left, top, _, _ = rect
        abs_x = left + x
        abs_y = top + y

        if self._error_sim:
            abs_x, abs_y = self._error_sim.maybe_misclick((abs_x, abs_y))

        self._move_humanized(abs_x, abs_y, pre_delay_distribution="reaction_time")
        pyautogui.click(abs_x, abs_y)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"PC tap at window ({x}, {y}) -> screen ({abs_x}, {abs_y})")

    def swipe(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration: float = 0.3,
    ) -> None:
        """Drag from start to end relative to the game window."""
        if not self._ensure_window_focus():
            logger.error("Cannot swipe: game window not available")
            return

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
                try:
                    for px, py in path[1:]:
                        pyautogui.moveTo(px, py)
                finally:
                    pyautogui.mouseUp()
                logger.debug(f"PC swipe humanized ({start}) -> ({end})")
                return

        pyautogui.moveTo(x1, y1)
        pyautogui.dragTo(x2, y2, duration=duration)
        logger.debug(f"PC swipe ({start}) -> ({end})")

    def key_back(self) -> None:
        """Press Escape (Android BACK equivalent on PC)."""
        if not self._ensure_window_focus():
            logger.error("Cannot press ESC: game window not available")
            return
        if self._timing:
            self._human_delay("reaction_time")
        pyautogui.press("esc")
        if self._timing:
            self._human_delay("click_interval")
        logger.debug("Pressed ESC (back)")

    def scroll(self, amount: int, x: int, y: int) -> None:
        """Scroll at window-relative coordinates."""
        if not self._ensure_window_focus():
            logger.error("Cannot scroll: game window not available")
            return
        rect = self.window_manager.get_client_rect()
        if rect is None:
            return
        left, top, _, _ = rect
        if self._timing:
            self._human_delay("reaction_time")
        pyautogui.scroll(amount, left + x, top + y)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"PC scroll {amount} at ({x}, {y})")

    def type_text(self, text: str, interval: float = 0.01) -> None:
        """Type text into the game window."""
        if not self._ensure_window_focus():
            logger.error("Cannot type: game window not available")
            return
        if self._timing:
            self._human_delay("reaction_time")
            # Human typists are irregular; sample per-character interval from
            # a log-normal distribution if no explicit interval was requested.
            if interval == 0.01:
                interval_ms = self._timing.sample("click_interval")
                interval = max(0.005, interval_ms / 1000.0)
        pyautogui.typewrite(text, interval=interval)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"Typed text: '{text}'")

    def press_key(self, key: str) -> None:
        """Press and release a keyboard key immediately (one tap).

        The game window is activated first so the keystroke reaches it.
        """
        if not self._ensure_window_focus():
            logger.error(f"Cannot press '{key}': game window not available")
            return

        if self._timing:
            self._human_delay("reaction_time")
        pyautogui.press(key)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"Pressed key '{key}'")

    def hold_key(self, key: str, duration: float) -> None:
        """Hold a keyboard key for a given duration."""
        if not self._ensure_window_focus():
            logger.error(f"Cannot hold '{key}': game window not available")
            return
        if self._timing:
            self._human_delay("reaction_time")
            # Add small fatigue-based jitter to the hold duration.
            jitter = random.uniform(-0.02, 0.05) if self._decision is None else (
                random.uniform(-0.02, 0.05) * (1.0 + self._decision.state.fatigue)
            )
            duration = max(0.05, duration + jitter)
        pyautogui.keyDown(key)
        try:
            time.sleep(duration)
        finally:
            pyautogui.keyUp(key)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"Held key '{key}' for {duration:.2f}s")

    def hold_key_native(self, key: str, duration: float) -> None:
        """Hold a keyboard key using win32api.keybd_event (bypasses some anti-bot blocks)."""
        if not self._ensure_window_focus():
            logger.error(f"Cannot hold '{key}' native: game window not available")
            return

        import win32api
        import win32con

        VK_MAP = {
            "up": win32con.VK_UP,
            "down": win32con.VK_DOWN,
            "left": win32con.VK_LEFT,
            "right": win32con.VK_RIGHT,
            "esc": win32con.VK_ESCAPE,
            "space": win32con.VK_SPACE,
        }
        vk = VK_MAP.get(key.lower())
        if vk is None:
            logger.warning(f"hold_key_native: unsupported key '{key}', falling back to hold_key")
            self.hold_key(key, duration)
            return

        if self._timing:
            self._human_delay("reaction_time")
            # Add small fatigue-based jitter to the hold duration.
            jitter = random.uniform(-0.02, 0.05) if self._decision is None else (
                random.uniform(-0.02, 0.05) * (1.0 + self._decision.state.fatigue)
            )
            duration = max(0.05, duration + jitter)

        win32api.keybd_event(vk, 0, 0, 0)
        try:
            time.sleep(duration)
        finally:
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        if self._timing:
            self._human_delay("click_interval")
        logger.debug(f"Held key '{key}' for {duration:.2f}s (native)")

    def hold_click_at(self, x: int, y: int, duration: float) -> None:
        """Hold a mouse click at window-relative coordinates.

        Moves the cursor along a humanized path, then presses and holds the
        left mouse button for the requested duration.
        """
        if not self._ensure_window_focus():
            logger.error("Cannot hold click: game window not available")
            return

        rect = self.window_manager.get_client_rect()
        if rect is None:
            logger.error("Cannot hold click: game window not found")
            return

        left, top, _, _ = rect
        abs_x = left + x
        abs_y = top + y

        self._move_humanized(abs_x, abs_y, pre_delay_distribution="reaction_time")
        if self._timing:
            # Add small fatigue-based jitter to the hold duration.
            jitter = random.uniform(-0.05, 0.15) if self._decision is None else (
                random.uniform(-0.05, 0.15) * (1.0 + self._decision.state.fatigue)
            )
            duration = max(0.1, duration + jitter)

        pyautogui.mouseDown()
        try:
            time.sleep(duration)
        finally:
            pyautogui.mouseUp()
        if self._timing:
            self._human_delay("click_interval")
        logger.info(
            f"PC hold-click at window ({x}, {y}) -> screen ({abs_x}, {abs_y}) "
            f"for {duration:.2f}s"
        )

    def share_decision_engine(self, decision_engine) -> None:
        """Share a DecisionEngine instance (e.g. from StateMachine).

        This keeps fatigue, frustration and distraction probabilities
        consistent across the input layer and all actions.
        """
        self._decision = decision_engine
        if self._error_sim is not None:
            self._error_sim.decision = decision_engine
        else:
            from rokbot.humanization.error_simulator import ErrorSimulator

            self._error_sim = ErrorSimulator(decision_engine)
        logger.debug("DecisionEngine shared with PCInput")

    def move_to_safe_zone(self) -> None:
        """Move mouse to a random spot along the bottom edge (taskbar area).

        Resting the cursor on the game taskbar keeps it away from central UI
        elements during screen capture while looking more human than a fixed
        corner. A small Gaussian jitter is applied so repeated calls do not
        land on exactly the same pixel.

        To avoid excessive cursor movement, this method is rate-limited and
        skipped when the cursor is already near the window edges.
        """
        if not self._ensure_window_focus():
            return
        rect = self.window_manager.get_client_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return

        now = time.monotonic()
        cooldown = 2.5 if not self._humanization_enabled else random.uniform(2.0, 5.0)
        if now - self._last_safe_zone_move_time < cooldown:
            logger.debug("Skipping safe-zone move: still within cooldown")
            return

        # Decide whether to move based on where the cursor currently sits.
        # Some edge zones are already safe and are skipped most of the time;
        # others still risk covering UI elements, so we move more often there.
        current = pyautogui.position()
        cx, cy = current.x, current.y
        mid_x = left + width // 2
        top_band = top + int(height * 0.125)
        bottom_band = bottom - int(height * 0.25)
        left_band = left + int(width * 0.20)
        right_band = right - int(width * 0.20)

        if cy <= top_band or (cy >= bottom_band and cx <= mid_x):
            # Cursor already rests in a safe area (top edge or bottom-left half).
            # For long-running sessions we avoid micro-adjustments here almost
            # all of the time; only occasionally nudge it to look alive.
            bypass_prob = 0.95
        elif cx <= left_band or cx >= right_band or (cy >= bottom_band and cx > mid_x):
            # Cursor is on a side edge or bottom-right: it may still cover UI,
            # so move it away more reliably.
            bypass_prob = 0.0
        else:
            # Center area: almost always move to avoid covering important UI.
            bypass_prob = 0.0

        if self._humanization_enabled and random.random() < bypass_prob:
            logger.debug(f"Skipping safe-zone move: cursor already safe (bypass {bypass_prob:.0%})")
            self._last_safe_zone_move_time = now
            return

        # Keep a modest margin inside the client area so the cursor stays
        # clearly within the window and away from the absolute border.
        margin_x = max(10, int(width * 0.02))
        margin_y = max(5, int(height * 0.02))

        target_x = random.randint(left + margin_x, max(left + margin_x, right - margin_x))
        target_y = bottom - margin_y

        if self._humanization_enabled:
            jitter_sigma = 2.0
            target_x = int(round(random.gauss(target_x, jitter_sigma)))
            target_y = int(round(random.gauss(target_y, jitter_sigma)))

        target_x = max(left + 1, min(target_x, right - 1))
        target_y = max(top + 1, min(target_y, bottom - 1))

        self._move_humanized(target_x, target_y, pre_delay_distribution="reaction_time")
        self._last_safe_zone_move_time = time.monotonic()
        logger.debug(f"Moved mouse to safe zone ({target_x - left}, {target_y - top}) relative to window")
