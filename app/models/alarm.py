# 담당: C팀원
import uuid
from datetime import datetime, time
from sqlalchemy import String, Time, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DiaryAlarm(Base):
    __tablename__ = "diary_alarms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    alarm_time: Mapped[time] = mapped_column(Time, nullable=False)
    repeat_days: Mapped[str | None] = mapped_column(String(30), nullable=True)   # MON,WED,FRI 형식, null=매일
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
