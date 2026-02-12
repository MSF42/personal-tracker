from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base exception for application errors."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Internal server error",
        code: str | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(AppError):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code="NOT_FOUND",
        )


class ConflictError(AppError):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code="CONFLICT",
        )


class ValidationError(AppError):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="VALIDATION_ERROR",
        )
