class ApplicationError(Exception):
    """Safe, public error without infrastructure details."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
