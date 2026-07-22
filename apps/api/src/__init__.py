from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.modules.dashboard.router import router as dashboard_router
from src.modules.google_health.router import router as google_health_router
from src.modules.habits.router import router as habits_router
from src.modules.identity.router import router as identity_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="LifeStats API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.include_router(identity_router, prefix="/api/v1")
    application.include_router(google_health_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(habits_router, prefix="/api/v1")

    @application.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(RuntimeError)
    async def runtime_error(_: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=502)

    return application


app = create_app()
