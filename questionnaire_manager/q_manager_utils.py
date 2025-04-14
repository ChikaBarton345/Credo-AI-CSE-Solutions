
class BaseError(Exception):
    

    """Generic base exception class for error handling."""

    def __init__(
        self,
        message: str,
        error_type: str = None,
        status_code: int = None,
        details: dict = None,
        source: str = None,
        timestamp: str = None,
        severity: str = None,
        error_line: str = None,
    ):
        """
        Initialize base error class with comprehensive context.

        Args:
            message: Main error message
            error_type: Type/category of error
            status_code: Status code (HTTP or custom)
            details: Additional error details as dictionary
            source: Where the error originated (function, class, module)
            timestamp: When the error occurred (defaults to current time)
            severity: Severity level of the error (e.g., "HIGH", "MEDIUM", "LOW")
            error_line: Line number of the error
        """
        from datetime import datetime

        self.message = message
        self.error_type = error_type or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        self.source = source or self._get_source()
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.severity = severity or "HIGH"
        self.error_line = error_line
        # Format the error message
        error_msg = [f"Error: {message}"]
        if error_type:
            error_msg.append(f"Type: {error_type}")
        if status_code:
            error_msg.append(f"Status: {status_code}")
        if source:
            error_msg.append(f"Source: {source}")
        if details:
            error_msg.append(f"Details: {details}")
        if error_line:
            error_msg.append(f"Line: {error_line}")
        super().__init__("\n".join(error_msg))

    def _get_source(self) -> str:
        """Get the source of the error from the stack trace."""
        import traceback

        tb = traceback.extract_stack()[-3]  # -3 to get the calling frame
        return f"{tb.filename}:{tb.lineno} in {tb.name}"

    def to_dict(self) -> dict:
        """Convert error to dictionary for logging or serialization."""
        return {
            "message": self.message,
            "error_type": self.error_type,
            "status_code": self.status_code,
            "details": self.details,
            "source": self.source,
            "timestamp": self.timestamp,
        }

class TriggersActionsError(BaseError):
    """Raised when triggers and actions creation fails."""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_type', 'TriggersActionsError')  
        super().__init__(message, **kwargs)

class ValueError(BaseError):
    """Raised when a value is not found ."""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_type', 'ValueError')  
        super().__init__(message, **kwargs)

class APIError(BaseError):
    """Raised when API requests fail"""
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_type', 'APIError')  
        super().__init__(message, **kwargs)

class QuestionnaireError(BaseError):
     def __init__(self, message: str, **kwargs):
        kwargs.setdefault('error_type', 'QuestionnaireError')  
        super().__init__(message, **kwargs)
