"""Scrcpy streaming client."""

import socket
from typing import Optional

from loguru import logger


class ScrcpyClient:
    """Minimal scrcpy client for video frame streaming."""

    def __init__(self, host: str = "127.0.0.1", port: int = 27183):
        self.host = host
        self.port = port
        self._socket: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to scrcpy server."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.host, self.port))
            logger.info(f"Connected to scrcpy at {self.host}:{self.port}")
            return True
        except OSError as e:
            logger.error(f"Failed to connect to scrcpy: {e}")
            return False

    def disconnect(self) -> None:
        """Close scrcpy connection."""
        if self._socket:
            self._socket.close()
            self._socket = None
            logger.info("Scrcpy disconnected")
