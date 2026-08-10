"""Safe, coded exceptions that may cross the Native Messaging boundary."""


class HostError(Exception):
    """Represent an expected failure using a stable public error code."""

    def __init__(self, code: str, message: str) -> None:
        """Initialize an error without including message content or secrets."""
        super().__init__(message)
        self.code = code


class CancelledError(HostError):
    """Signal cooperative cancellation of an archive job."""

    def __init__(self) -> None:
        """Initialize the stable cancellation response."""
        super().__init__("cancelled", "The archive operation was cancelled.")
