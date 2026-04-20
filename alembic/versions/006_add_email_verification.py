"""이메일 인증 & 비밀번호 재설정 지원을 위한 스키마 추가

Revision ID: 006
Revises: 005
Create Date: 2026-04-16

[변경 내용]
- users.is_verified      추가 (BOOLEAN, NOT NULL, default false) — 이메일 인증 완료 여부
- email_tokens 테이블    신규 생성 — 이메일 인증(매직 링크) & 비밀번호 재설정 토큰 공용
"""
import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.is_verified 추가 (기존 사용자는 false로 초기화)
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
    )

    # email_tokens 테이블 생성
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("token_type", sa.String(30), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_email_tokens_token", "email_tokens", ["token"])
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_email_tokens_user_id", table_name="email_tokens")
    op.drop_constraint("uq_email_tokens_token", "email_tokens", type_="unique")
    op.drop_table("email_tokens")
    op.drop_column("users", "is_verified")
