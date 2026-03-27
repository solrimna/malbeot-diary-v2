import uuid
from datetime import time, datetime
from typing import Optional

from pydantic import BaseModel


class AlarmCreate(BaseModel):
    alarm_time: time
    repeat_days: Optional[list[str]] = None
    is_enabled: bool = True


class AlarmResponse(BaseModel):
    id: int
    user_id: uuid.UUID
    alarm_time: time
    repeat_days: Optional[str] = None
    is_enabled: bool
    created_at: datetime
    last_triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True
