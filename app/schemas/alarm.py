import uuid
from datetime import datetime, time

from pydantic import BaseModel


class AlarmCreate(BaseModel):
    alarm_time: time
    repeat_days: list[str] | None = None
    is_enabled: bool = True


class AlarmResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    alarm_time: time
    repeat_days: str | None = None
    is_enabled: bool
    created_at: datetime
    last_triggered_at: datetime | None = None

    class Config:
        from_attributes = True
