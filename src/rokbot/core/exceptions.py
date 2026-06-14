"""Core exceptions for ROK Bot Engine v2."""


class BotException(Exception):
    """Base exception for bot errors."""
    pass


class StuckError(BotException):
    """Raised when the bot is detected as stuck in a state."""
    pass


class RecoveryError(BotException):
    """Raised when error recovery fails after maximum retries."""
    pass
