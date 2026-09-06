import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config.settings import Settings, get_settings
from src.db.database import DATABASE_PATH
from src.db.migrations import run_migrations
from src.errors import AppError
from src.middleware.logging import RequestLoggingMiddleware
from src.routes.countdowns import router as countdowns_router
from src.routes.exercises import router as exercise_router
from src.routes.habits import router as habits_router
from src.routes.health import router
from src.routes.images import router as images_router
from src.routes.measurements import router as measurements_router
from src.routes.running import router as running_router
from src.routes.search import router as search_router
from src.routes.settings import router as settings_router
from src.routes.tasks import router as tasks_router
from src.routes.today import router as today_router
from src.routes.workout_logs import router as workout_logs_router
from src.routes.workout_routines import router as workout_routine_router


def ensure_data_dirs(settings: Settings) -> None:
    # Also called from create_app(): mounting StaticFiles raises if the uploads
    # directory is missing, and that happens before lifespan runs.
    os.makedirs("data", exist_ok=True)  # Create data/ if missing
    os.makedirs(settings.uploads_path, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: create data directory, ensure DB exists
    settings = get_settings()
    ensure_data_dirs(settings)
    await run_migrations(DATABASE_PATH)
    print("Starting up...")
    yield
    # Shutdown: cleanup if needed
    print("Shutting down...")


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_data_dirs(settings)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = []
        for error in exc.errors():
            field = error["loc"][-1] if error["loc"] else None
            msg = error["msg"]
            if field and field != "body":
                label = str(field).replace("_", " ").capitalize()
                messages.append(f"{label}: {msg}")
            else:
                messages.append(msg)
        return JSONResponse(
            status_code=422,
            content={
                "error": "; ".join(messages),
                "code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the error here (we'll add proper logging in Step 19)
        print(f"Unexpected error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
            },
        )

    # Register routes
    app.include_router(router)  # bare paths: /health, /health/live, /health/ready, etc.
    app.include_router(tasks_router)
    app.include_router(habits_router)
    app.include_router(running_router)
    app.include_router(exercise_router)
    app.include_router(workout_routine_router)
    app.include_router(workout_logs_router)
    app.include_router(measurements_router)
    app.include_router(countdowns_router)
    app.include_router(images_router)
    app.include_router(settings_router)
    app.include_router(search_router)
    app.include_router(today_router)

    app.mount("/uploads", StaticFiles(directory=settings.uploads_path), name="uploads")

    return app
