import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.db.database import DATABASE_PATH
from src.db.migrations import run_migrations
from src.errors import AppError
from src.middleware.logging import RequestLoggingMiddleware
from src.routes.exercises import router as exercise_router
from src.routes.health import router
from src.routes.running import router as running_router
from src.routes.tasks import router as tasks_router
from src.routes.workout_logs import router as workout_logs_router
from src.routes.workout_routines import router as workout_routine_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create data directory, ensure DB exists
    os.makedirs("data", exist_ok=True)  # Create data/ if missing
    await run_migrations(DATABASE_PATH)
    print("Starting up...")
    yield
    # Shutdown: cleanup if needed
    print("Shutting down...")


def create_app():
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)

    # Exception handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": exc.code,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
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
    app.include_router(router)
    app.include_router(tasks_router)
    app.include_router(running_router)
    app.include_router(exercise_router)
    app.include_router(workout_routine_router)
    app.include_router(workout_logs_router)
    return app
