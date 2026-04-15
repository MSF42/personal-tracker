from fastapi import APIRouter, Depends, Query

from src.db.database import get_db
from src.repositories.search_repository import SQLiteSearchRepository

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


async def get_search_repository(db=Depends(get_db)):
    return SQLiteSearchRepository(db)


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    repo: SQLiteSearchRepository = Depends(get_search_repository),
):
    return {"hits": await repo.query(q)}
