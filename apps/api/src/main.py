import uvicorn

from src import app as app


def run() -> None:
    uvicorn.run("src:app", app_dir="apps/api", reload=True)
