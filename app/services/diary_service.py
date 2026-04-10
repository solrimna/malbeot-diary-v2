# 담당 : A팀원 유가영
import uuid
from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diary import Diary
from app.models.diary_summary import DiarySummary
from app.models.hashtag import DiaryHashtag, Hashtag
from app.schemas.diary import DiaryCreate, DiaryUpdate


class DiaryService:

    # ── 일기 생성 ───────────────────────────────
    async def create_diary(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: DiaryCreate,
    ) -> Diary:
        diary = Diary(
            user_id=user_id,
            persona_id=data.persona_id,
            title=data.title,
            emotion=data.emotion,
            weather=data.weather,
            content=data.content,
            input_type=data.input_type,
            diary_date=data.diary_date,
        )
        db.add(diary)
        await db.flush()  # id 먼저 확보

        # 해시태그 저장 (Hashtag 생성 → DiaryHashtag 연결)
        for tag in data.hashtags:
            tag_name = tag.strip()
            # 기존 태그 조회
            existing = await db.execute(
                select(Hashtag).where(
                    Hashtag.user_id == user_id,
                    Hashtag.name == tag_name,
                )
            )
            hashtag = existing.scalar_one_or_none()
            # 없으면 새로 생성
            if not hashtag:
                hashtag = Hashtag(user_id=user_id, name=tag_name)
                db.add(hashtag)
                await db.flush()
            # 일기-태그 연결
            db.add(DiaryHashtag(diary_id=diary.id, hashtag_id=hashtag.id))

        await db.commit()
        await db.refresh(diary)
        return diary

    # ── 목록 조회 (날짜 최신순 + 해시태그 필터 + 날짜 조회 + 커서 페이지네이션) ────
    # date:   특정 날짜 일기만 조회 (지정 시 after/before/limit 무시)
    # after:  이 날짜 이후 일기만 조회 (캘린더 월별 조회 시 월 시작일)
    # before: 이 날짜보다 이전 일기만 조회 (커서 or 캘린더 월별 조회 시 다음달 1일)
    # limit:  한 번에 반환할 최대 개수 (기본 20개 → 데스크탑 기준 약 15권 표시)
    async def get_diaries(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        tag: str | None = None,
        date: date | None = None,
        after: date | None = None,
        before: date | None = None,
        limit: int = 20,
    ) -> list[Diary]:
        stmt = (
            select(Diary)
            .where(Diary.user_id == user_id)
            .order_by(desc(Diary.diary_date))
        )
        if tag:
            stmt = (
                stmt
                .join(DiaryHashtag, Diary.id == DiaryHashtag.diary_id)
                .join(Hashtag, DiaryHashtag.hashtag_id == Hashtag.id)
                .where(Hashtag.name == tag)
            )
        # 특정 날짜 조회: 해당 날짜 일기만 반환 (after/before/limit 적용 안 함)
        if date:
            stmt = stmt.where(Diary.diary_date == date)
            result = await db.execute(stmt)
            return result.scalars().all()

        # 날짜 범위: after/before 조합으로 월별 조회 등에 사용
        if after:
            stmt = stmt.where(Diary.diary_date >= after)
        if before:
            stmt = stmt.where(Diary.diary_date < before)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()

    # ── 단건 조회 ───────────────────────────────
    async def get_diary(
        self,
        db: AsyncSession,
        diary_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Diary | None:
        stmt = select(Diary).where(
            Diary.id == diary_id,
            Diary.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ── 수정 ────────────────────────────────────
    async def update_diary(
        self,
        db: AsyncSession,
        diary: Diary,
        data: DiaryUpdate,
    ) -> Diary:
        if data.title is not None:
            diary.title = data.title
        if data.emotion is not None:
            diary.emotion = data.emotion
        if data.weather is not None:
            diary.weather = data.weather
        if data.content is not None:
            diary.content = data.content
        if data.diary_date is not None:
            diary.diary_date = data.diary_date
        if data.persona_id is not None:
            diary.persona_id = data.persona_id

        await db.commit()
        await db.refresh(diary)
        return diary

    # ── 삭제 ────────────────────────────────────
    async def delete_diary(
        self,
        db: AsyncSession,
        diary: Diary,
    ) -> None:
        from sqlalchemy import select as sa_select

        from app.models.ai_feedback import AiFeedback
        from app.models.hashtag import DiaryHashtag

        # 연결된 해시태그 먼저 삭제
        stmt_dh = sa_select(DiaryHashtag).where(DiaryHashtag.diary_id == diary.id)
        result_dh = await db.execute(stmt_dh)
        for dh in result_dh.scalars().all():
            await db.delete(dh)

        # 연결된 피드백 먼저 삭제
        stmt_fb = sa_select(AiFeedback).where(AiFeedback.diary_id == diary.id)
        result_fb = await db.execute(stmt_fb)
        feedback = result_fb.scalar_one_or_none()
        if feedback:
            await db.delete(feedback)

        await db.flush()
        await db.delete(diary)
        await db.commit()

    # ── 요약 갱신 (내용 변경 시 기존 삭제 후 재생성) ─
    async def update_summary(
        self,
        db: AsyncSession,
        diary: Diary,
    ) -> DiarySummary | None:
        existing = await db.execute(
            select(DiarySummary).where(DiarySummary.diary_id == diary.id)
        )
        summary = existing.scalar_one_or_none()
        if summary:
            await db.delete(summary)
            await db.commit()
        return await self.create_summary(db, diary)

    # ── 요약 생성 & 저장 ──────────────────────────
    async def create_summary(
        self,
        db: AsyncSession,
        diary: Diary,
    ) -> DiarySummary | None:
        from app.services.gpt_service import gpt_service

        summary_text = await gpt_service.generate_summary(diary.content)
        if not summary_text:
            return None

        summary = DiarySummary(
            user_id=diary.user_id,
            diary_id=diary.id,
            summary=summary_text,
            diary_date=diary.diary_date,
        )
        db.add(summary)
        await db.commit()
        await db.refresh(summary)
        return summary

    # ── 해시태그 추가 ─────────────────────────────
    async def add_hashtags(
        self,
        db: AsyncSession,
        diary_id: uuid.UUID,
        user_id: uuid.UUID,
        hashtags: list[str],
    ) -> None:
        for tag in hashtags:
            tag_name = tag.strip()
            if not tag_name:
                continue
            # 기존 태그 조회
            existing = await db.execute(
                select(Hashtag).where(
                    Hashtag.user_id == user_id,
                    Hashtag.name == tag_name,
                )
            )
            hashtag = existing.scalar_one_or_none()
            # 없으면 새로 생성
            if not hashtag:
                hashtag = Hashtag(user_id=user_id, name=tag_name)
                db.add(hashtag)
                await db.flush()
            # 중복 연결 확인
            existing_link = await db.execute(
                select(DiaryHashtag).where(
                    DiaryHashtag.diary_id == diary_id,
                    DiaryHashtag.hashtag_id == hashtag.id,
                )
            )
            if not existing_link.scalar_one_or_none():
                db.add(DiaryHashtag(diary_id=diary_id, hashtag_id=hashtag.id))
        await db.commit()
