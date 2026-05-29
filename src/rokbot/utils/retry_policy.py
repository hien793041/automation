"""Exponential backoff with jitter retry policy."""

import random
import time
from typing import Callable, Optional, Type, Tuple

from loguru import logger


class RetryPolicy:
    """Configurable retry policy with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay_seconds
        self.max_delay = max_delay_seconds
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions

    def execute(self, func: Callable, *args, **kwargs):
        """Execute func with retry logic."""
        last_exception = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{self.max_attempts} failed: {e}")
                if attempt < self.max_attempts:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** (attempt - 1)),
                        self.max_delay,
                    )
                    if self.jitter:
                        delay = delay * (0.5 + random.random())
                    logger.info(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
        raise last_exception
