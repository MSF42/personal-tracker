from fastapi import APIRouter, Depends

from src.config.settings import get_settings
from src.db.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Basic health check - is the server running?"""
    return {"status": "ok"}


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the process alive?"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness(db=Depends(get_db)):
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
        return {
            "status": "not_ready",
            "checks": {
                "database": f"unhealthy: {str(e)}",
            },
        }


@router.get("/health/info")
async def info():
    """Application info endpoint."""
    settings = get_settings()
    return {
        "environment": settings.environment,
        "version": settings.api_version,
    }
