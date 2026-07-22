from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lifestats.dashboard.presentation.router import router as dashboard_router
from lifestats.google_health.presentation.router import router as google_health_router
from lifestats.habits.presentation.router import router as habits_router
from lifestats.identity.presentation.router import router as identity_router

app = FastAPI(
    title="LifeStats API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(identity_router, prefix="/api/v1")
app.include_router(google_health_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(habits_router, prefix="/api/v1")


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RuntimeError)
async def runtime_error(_: Request, exc: RuntimeError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=502)
