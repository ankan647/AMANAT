from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class UnauthenticatedError(ApiError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__("UNAUTHENTICATED", message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(ApiError):
    def __init__(self, message: str = "You are not allowed to do this.", details=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__("FORBIDDEN", message, status.HTTP_403_FORBIDDEN, details)


class SodViolationError(ApiError):
    def __init__(self, message: str, rule: str) -> None:
        super().__init__(
            "SOD_VIOLATION", message, status.HTTP_403_FORBIDDEN, details={"rule": rule}
        )


class NotFoundError(ApiError):
    def __init__(self, message: str = "Not found.") -> None:
        super().__init__("NOT_FOUND", message, status.HTTP_404_NOT_FOUND)


class ConflictError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message, status.HTTP_409_CONFLICT)


class InvalidStateError(ApiError):
    def __init__(self, message: str, details=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__("INVALID_STATE", message, status.HTTP_409_CONFLICT, details)


class ValidationFieldsError(ApiError):
    def __init__(self, fields: list[dict[str, str]]) -> None:
        super().__init__(
            "VALIDATION_ERROR",
            "Validation failed.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"fields": fields},
        )


class RateLimitedError(ApiError):
    def __init__(self, message: str = "Too many requests.") -> None:
        super().__init__("RATE_LIMITED", message, status.HTTP_429_TOO_MANY_REQUESTS)


def _envelope(code: str, message: str, request_id: str, details: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, request_id, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        fields = [
            {"path": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                "VALIDATION_ERROR", "Validation failed.", request_id, {"fields": fields}
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "INTERNAL")
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail), request_id),
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL", "Internal server error.", request_id),
        )
