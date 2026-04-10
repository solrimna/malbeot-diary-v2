"""add diary_summaries table and memory column to personas

Revision ID: 003
Revises: 002
Create Date: 2026-03-31

"""
import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # diary_summaries 테이블 생성
    op.create_table(
        "diary_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("diary_id", sa.UUID(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("diary_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diary_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diary_id"], ["diaries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_diary_summaries_user_date", "diary_summaries", ["user_id", "diary_date"])

    # personas 테이블에 memory 컬럼 추가
    # 온보딩 Q&A에서 입력한 "기억해줬으면 하는 것"을 저장, 피드백 시스템 프롬프트에 활용
    op.add_column(
        "personas",
        sa.Column("memory", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("personas", "memory")
    op.drop_index("ix_diary_summaries_user_date", table_name="diary_summaries")
    op.drop_table("diary_summaries")
