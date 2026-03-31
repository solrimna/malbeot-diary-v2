import uuid
from datetime import date, datetime
from sqlalchemy import Text, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DiarySummary(Base):
    __tablename__ = "diary_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    diary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("diaries.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)   # GPT가 생성한 1~2문장 요약
    diary_date: Mapped[date] = mapped_column(Date, nullable=False)  # 정렬용 비정규화
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
