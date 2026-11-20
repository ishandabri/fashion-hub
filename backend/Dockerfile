FROM python:3.12-slim
WORKDIR /app
ARG APP_VERSION=0.1.0
ARG APP_REVISION=dev
ARG APP_BUILT_AT=development
ENV APP_VERSION=$APP_VERSION APP_REVISION=$APP_REVISION APP_BUILT_AT=$APP_BUILT_AT
COPY pyproject.toml .
COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations
RUN pip install --no-cache-dir .[test]
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

