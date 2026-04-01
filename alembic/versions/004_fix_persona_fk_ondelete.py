"""fix FK ondelete constraints (persona 삭제, 회원 탈퇴 대비)

Revision ID: 004
Revises: 003
Create Date: 2026-04-01

[변경 내용]
페르소나 삭제:
  - diaries.persona_id        → ON DELETE SET NULL
  - ai_feedbacks.persona_id   → ON DELETE CASCADE

회원 탈퇴 대비:
  - diaries.user_id           → ON DELETE CASCADE
  - personas.user_id          → ON DELETE CASCADE
  - alarms.user_id            → ON DELETE CASCADE
  - push_subscriptions.user_id → ON DELETE CASCADE
  - hashtags.user_id          → ON DELETE CASCADE
  - diary_hashtags.hashtag_id → ON DELETE CASCADE
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 페르소나 삭제 관련 ──────────────────────────────────────
    op.drop_constraint("diaries_persona_id_fkey", "diaries", type_="foreignkey")
    op.create_foreign_key(
        "diaries_persona_id_fkey", "diaries", "personas",
        ["persona_id"], ["id"], ondelete="SET NULL",
    )

    op.drop_constraint("ai_feedbacks_persona_id_fkey", "ai_feedbacks", type_="foreignkey")
    op.create_foreign_key(
        "ai_feedbacks_persona_id_fkey", "ai_feedbacks", "personas",
        ["persona_id"], ["id"], ondelete="CASCADE",
    )

    # ── 회원 탈퇴 대비 ─────────────────────────────────────────
    op.drop_constraint("diaries_user_id_fkey", "diaries", type_="foreignkey")
    op.create_foreign_key(
        "diaries_user_id_fkey", "diaries", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("personas_user_id_fkey", "personas", type_="foreignkey")
    op.create_foreign_key(
        "personas_user_id_fkey", "personas", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("alarms_user_id_fkey", "alarms", type_="foreignkey")
    op.create_foreign_key(
        "alarms_user_id_fkey", "alarms", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("push_subscriptions_user_id_fkey", "push_subscriptions", type_="foreignkey")
    op.create_foreign_key(
        "push_subscriptions_user_id_fkey", "push_subscriptions", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("hashtags_user_id_fkey", "hashtags", type_="foreignkey")
    op.create_foreign_key(
        "hashtags_user_id_fkey", "hashtags", "users",
        ["user_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("diary_hashtags_hashtag_id_fkey", "diary_hashtags", type_="foreignkey")
    op.create_foreign_key(
        "diary_hashtags_hashtag_id_fkey", "diary_hashtags", "hashtags",
        ["hashtag_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("diaries_persona_id_fkey", "diaries", type_="foreignkey")
    op.create_foreign_key(
        "diaries_persona_id_fkey", "diaries", "personas", ["persona_id"], ["id"],
    )

    op.drop_constraint("ai_feedbacks_persona_id_fkey", "ai_feedbacks", type_="foreignkey")
    op.create_foreign_key(
        "ai_feedbacks_persona_id_fkey", "ai_feedbacks", "personas", ["persona_id"], ["id"],
    )

    op.drop_constraint("diaries_user_id_fkey", "diaries", type_="foreignkey")
    op.create_foreign_key(
        "diaries_user_id_fkey", "diaries", "users", ["user_id"], ["id"],
    )

    op.drop_constraint("personas_user_id_fkey", "personas", type_="foreignkey")
    op.create_foreign_key(
        "personas_user_id_fkey", "personas", "users", ["user_id"], ["id"],
    )

    op.drop_constraint("alarms_user_id_fkey", "alarms", type_="foreignkey")
    op.create_foreign_key(
        "alarms_user_id_fkey", "alarms", "users", ["user_id"], ["id"],
    )

    op.drop_constraint("push_subscriptions_user_id_fkey", "push_subscriptions", type_="foreignkey")
    op.create_foreign_key(
        "push_subscriptions_user_id_fkey", "push_subscriptions", "users", ["user_id"], ["id"],
    )

    op.drop_constraint("hashtags_user_id_fkey", "hashtags", type_="foreignkey")
    op.create_foreign_key(
        "hashtags_user_id_fkey", "hashtags", "users", ["user_id"], ["id"],
    )

    op.drop_constraint("diary_hashtags_hashtag_id_fkey", "diary_hashtags", type_="foreignkey")
    op.create_foreign_key(
        "diary_hashtags_hashtag_id_fkey", "diary_hashtags", "hashtags", ["hashtag_id"], ["id"],
    )
