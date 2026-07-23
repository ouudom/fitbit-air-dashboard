import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.router import api_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="LifeStats API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(RuntimeError)
    async def runtime_error(_: Request, exc: RuntimeError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=502)

    return application


app = create_app()


def run() -> None:
    uvicorn.run("src.main:app", app_dir="apps/api", reload=True)
