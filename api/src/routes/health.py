from fastapi import APIRouter, Depends

from src.db.database import get_db

router = APIRouter()


@router.get("/health", summary="Health check", status_code=200)
def health_check():
    return {"status": "ok"}


@router.get("/api/v1/ping", summary="Ping", status_code=200)
def ping():
    return {"message": "pong"}


@router.get("/db-test")
async def db_test(db=Depends(get_db)):
    cursor = await db.execute("SELECT 1")
    result = await cursor.fetchone()
    return {"result": result[0]}
