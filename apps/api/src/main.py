import logging
from time import perf_counter

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from src.api.router import api_router
from src.core.config import get_settings
from src.core.logging import (
    REQUEST_ID_HEADER,
    bind_request_id,
    configure_logging,
    normalize_request_id,
    reset_request_id,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env, settings.log_level)
    application = FastAPI(
        title="LifeStats API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.middleware("http")
    async def request_logging(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = bind_request_id(request_id)
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            logger.exception(
                "HTTP request failed",
                extra={
                    "event": "http_request_failed",
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        finally:
            level = logging.DEBUG if request.url.path == "/healthz" else logging.INFO
            logger.log(
                level,
                "HTTP request completed",
                extra={
                    "event": "http_request_completed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
            )
            reset_request_id(token)

    @application.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(RuntimeError)
    async def runtime_error(request: Request, exc: RuntimeError) -> JSONResponse:
        logger.error(
            "Runtime error handled",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={
                "event": "runtime_error_handled",
                "method": request.method,
                "path": request.url.path,
                "status_code": 502,
            },
        )
        return JSONResponse({"detail": str(exc)}, status_code=502)

    return application


app = create_app()


def run() -> None:
    uvicorn.run("src.main:app", app_dir="apps/api", reload=True)
