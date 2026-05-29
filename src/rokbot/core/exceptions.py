"""Core exceptions for ROK Bot Engine v2."""


class BotException(Exception):
    """Base exception for bot errors."""
    pass


class StuckError(BotException):
    """Raised when the bot is detected as stuck in a state."""
    pass


class VisionError(BotException):
    """Raised when vision pipeline fails to detect required elements."""
    pass


class InputError(BotException):
    """Raised when input execution fails or cannot be verified."""
    pass


class ConfigError(BotException):
    """Raised when configuration is invalid or missing."""
    pass


class RecoveryError(BotException):
    """Raised when error recovery fails after maximum retries."""
    pass
