"""Per-session structured logging."""

from datetime import datetime
from pathlib import Path

from loguru import logger


class SessionLogger:
    """Configure per-session log files."""

    def __init__(self, log_dir: Path, session_id: str):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.log_path = self.log_dir / f"{session_id}.log"
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Add file sink for this session."""
        logger.add(
            self.log_path,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            filter=lambda record: record["extra"].get("session_id") == self.session_id,
        )

    def get_contextual_logger(self):
        """Return a logger bound to this session."""
        return logger.bind(session_id=self.session_id)
