"""users 테이블에 email, auth_provider, social_id 추가 및 password_hash nullable 변경

Revision ID: 005
Revises: 004
Create Date: 2026-04-13

[변경 내용]
- users.email          추가 (VARCHAR 255, UNIQUE, nullable) — 비밀번호 찾기 / 소셜 로그인 식별자
- users.auth_provider  추가 (VARCHAR 20, NOT NULL, default 'local') — local | google | kakao
- users.social_id      추가 (VARCHAR 255, nullable) — 소셜 provider 고유 ID
- users.password_hash  nullable 변경 — 소셜 로그인 가입자는 비밀번호 없음
"""
import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # email 컬럼 추가
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # auth_provider 컬럼 추가 (기존 사용자는 모두 'local')
    op.add_column(
        "users",
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="local"),
    )

    # social_id 컬럼 추가
    op.add_column("users", sa.Column("social_id", sa.String(255), nullable=True))

    # password_hash nullable 변경
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_column("users", "social_id")
    op.drop_column("users", "auth_provider")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "email")
