class ShutdownException(Exception):
    """Custom exception to signal a shutdown event."""

    def __init__(self, message: str):
        super().__init__(message)
