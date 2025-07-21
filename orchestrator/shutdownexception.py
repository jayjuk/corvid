from utils import exit
import logging


class ShutdownException(Exception):
    """Custom exception to signal a shutdown event."""

    def __init__(self, logger: logging.Logger, message: str):
        super().__init__(logger, message)
        exit(logger, message)
