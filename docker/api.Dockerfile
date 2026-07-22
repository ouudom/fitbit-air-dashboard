FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY apps/api ./apps/api
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 lifestats && chown -R lifestats:lifestats /app
USER lifestats
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
