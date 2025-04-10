class VigilantError(Exception):
    """Base exception for Vigilant errors."""
    pass


class FormattedVigilantError(VigilantError):
    """Base class for Vigilant errors with specific formatting."""
    error_header = "[ **** Vigilant Error **** ]"

    def __init__(self, message: str):
        self.original_message = message
        super().__init__(message)

    def formatted_message(self) -> str:
        return f"Error: {self.original_message}"

    def __str__(self) -> str:
        return self.formatted_message()


class BatcherInvalidTokenError(FormattedVigilantError):
    """Raised when the token is invalid (401 Unauthorized)."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message)

    def formatted_message(self) -> str:
        usage_header = "[ **** Correct Usage **** ]"
        details = """The token you have provided is invalid.
Please generate a new token by visiting: https://dashboard.vigilant.run/settings/project/api
If the issue persists, please contact support@vigilant.run"""
        example = """"""
        return f"{self.error_header}\n\n{details}\n\n{usage_header}\n\n{example}\n\nOriginal error: {self.original_message}"


class BatcherInternalServerError(FormattedVigilantError):
    """Raised for internal server errors or unexpected statuses."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message=message)

    def formatted_message(self) -> str:
        details = """The server is experiencing issues.
Please contact support@vigilant.run"""
        return f"{self.error_header}\n\n{details}\n\nOriginal error: {self.original_message}"


class NotInitializedError(FormattedVigilantError):
    """Raised when the Vigilant SDK is not initialized."""

    def __init__(self, message: str = "Vigilant SDK not initialized"):
        super().__init__(message=message)

    def formatted_message(self) -> str:
        details = """The Vigilant SDK is not initialized.
Please call init_vigilant() before using the SDK."""
        return f"{self.error_header}\n\n{details}\n\nOriginal error: {self.original_message}"
