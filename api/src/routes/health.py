from typing import Any

from aiosqlite import Connection
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.config.settings import get_settings
from src.db.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check - is the server running?"""
    return {"status": "ok"}


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Kubernetes liveness probe - is the process alive?"""
    return {"status": "alive"}


@router.get("/health/ready", response_model=None)
async def readiness(db: Connection = Depends(get_db)) -> dict[str, Any] | JSONResponse:
    """Kubernetes readiness probe - can we serve traffic?"""
    try:
        await db.execute("SELECT 1")
        return {
            "status": "ready",
            "checks": {
                "database": "healthy",
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {
                    "database": f"unhealthy: {str(e)}",
                },
            },
        )


@router.get("/health/info")
async def info() -> dict[str, str]:
    """Application info endpoint."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "version": settings.api_version,
    }
