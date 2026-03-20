from pydantic import BaseModel


class UpdateSettingRequest(BaseModel):
    value: str
