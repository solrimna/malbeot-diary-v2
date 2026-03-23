from sqlalchemy import Column, Integer, String, Boolean, Time, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    alarm_time = Column(Time, nullable=False)
    repeat_days = Column(String, nullable=False)  # 예: MON,WED,FRI
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_triggered_at = Column(DateTime, nullable=True)