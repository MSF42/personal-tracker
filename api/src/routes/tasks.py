from fastapi import APIRouter, Depends, Query

from src.db.database import get_db
from src.errors import NotFoundError
from src.models.task import CreateTaskRequest, TaskResponse, UpdateTaskRequest
from src.repositories.task_repository import SQLiteTaskRepository

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


async def get_task_repository(db=Depends(get_db)):
    return SQLiteTaskRepository(db)


@router.post("", status_code=201, response_model=TaskResponse)
async def create_task(
    task: CreateTaskRequest,
    repo: SQLiteTaskRepository = Depends(get_task_repository),
):
    return await repo.create(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    repo: SQLiteTaskRepository = Depends(get_task_repository),
):
    task = await repo.find_by_id(task_id)
    if task is None:
        raise NotFoundError("Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: UpdateTaskRequest,
    repo: SQLiteTaskRepository = Depends(get_task_repository),
):
    task = await repo.update(task_id, data)
    if task is None:
        raise NotFoundError("Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    repo: SQLiteTaskRepository = Depends(get_task_repository),
):
    deleted = await repo.delete(task_id)
    if not deleted:
        raise NotFoundError("Task not found")


@router.get("")
async def list_tasks(
    completed: bool | None = None,
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: SQLiteTaskRepository = Depends(get_task_repository),
):
    tasks, total = await repo.find_with_filters(
        completed=completed,
        category=category,
        limit=limit,
        offset=offset,
    )
    return {
        "data": tasks,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(tasks) < total,
    }
