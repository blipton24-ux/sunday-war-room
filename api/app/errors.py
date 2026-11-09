"""One error shape for the whole API: {"detail": "...", "code": "..."} (docs/Specs/API.md)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_responses() -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for authenticated routers, so the generated client types errors.

    Declared on routers, not per route: every code here can occur somewhere in the router,
    and they all share one body shape.
    """
    from app.schemas import ErrorOut  # local import: schemas must not depend on errors

    descriptions = {
        401: "Missing, invalid or expired token",
        404: "Not found (also returned for another user's league)",
        409: "Not ready yet (e.g. first sync unfinished, or no team chosen)",
        422: "Invalid request",
        429: "Rate limited",
    }
    return {code: {"model": ErrorOut, "description": d} for code, d in descriptions.items()}


class ApiError(Exception):
    """Raise this from anywhere in a request to return a clean JSON error."""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail


class NotFound(ApiError):
    def __init__(self, detail: str = "Not found", code: str = "not_found") -> None:
        super().__init__(404, code, detail)


class Unauthorized(ApiError):
    def __init__(self, detail: str = "Not signed in", code: str = "unauthorized") -> None:
        super().__init__(401, code, detail)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            {"detail": exc.detail, "code": exc.code}, status_code=exc.status_code, headers=headers
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 429: "rate_limited"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(
            {"detail": str(exc.detail), "code": code},
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ()))
        return JSONResponse(
            {"detail": f"{where}: {first.get('msg', 'invalid request')}", "code": "invalid"},
            status_code=422,
        )
