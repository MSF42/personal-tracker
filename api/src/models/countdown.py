from pydantic import BaseModel, Field


class CountdownResponse(BaseModel):
    id: int
    title: str
    date: str
    created_at: str
    updated_at: str


class CreateCountdownRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date, YYYY-MM-DD")


class UpdateCountdownRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
