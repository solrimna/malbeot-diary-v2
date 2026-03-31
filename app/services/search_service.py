# 담당 : A팀원 유가영
# 2026-03-31 나솔림 수정 (검색 성능 개선)
#
# [기존 문제]
# 1. query_keywords = query.replace(" ", "") 로 변수를 만들었으나 이후 코드에서 한 번도 사용되지 않는 데드코드
# 2. 1차 필터링(query.split() 기반 단순 문자열 포함 여부)을 하더라도
#    필터 통과한 일기의 원문(content)을 그대로 GPT에 전달하기 때문에
#    토큰 절감 효과가 없고 실질적인 필터링 의미가 없음
# 3. 매칭 결과가 없으면 최근 20개 일기 원문을 그대로 GPT에 전달
#
# [개선 방향]
# - hashtags 테이블로 1차 SQL 필터링 (토큰 소모 없음)
# - 매칭된 일기의 summary(요약)만 GPT에 전달 (원문 대비 토큰 대폭 감소)
# - summary가 없는 일기는 최근 30개 summary로 폴백
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import uuid
import logging

logger = logging.getLogger(__name__)
from openai import AsyncOpenAI
from app.config import get_settings
from app.models.diary import Diary
from app.models.diary_summary import DiarySummary
from app.models.hashtag import Hashtag, DiaryHashtag

settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# 한국어 조사/어미 제거 (해시태그 매칭 정확도 향상)
# 예: "운동을" → "운동", "갔더라?" → "갔더라"
_KO_PARTICLES = ("을", "를", "이", "가", "은", "는", "도", "만", "로", "으로",
                 "에", "의", "과", "와", "랑", "이랑", "서", "에서")

def _strip_particle(word: str) -> str:
    word = word.rstrip("?!.,~")
    for particle in sorted(_KO_PARTICLES, key=len, reverse=True):  # 긴 것부터
        if word.endswith(particle) and len(word) > len(particle):
            return word[: -len(particle)]
    return word


class SearchService:

    async def _filter_by_hashtags(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        keywords: list[str],
    ) -> list[uuid.UUID]:
        """쿼리 키워드와 매칭되는 diary_id 목록 반환 (hashtags 테이블 기준, SQL only)"""
        conditions = [Hashtag.name.ilike(f"%{kw}%") for kw in keywords]
        stmt = (
            select(DiaryHashtag.diary_id)
            .join(Hashtag, DiaryHashtag.hashtag_id == Hashtag.id)
            .where(Hashtag.user_id == user_id, or_(*conditions))
            .distinct()
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    # ── 일기 검색: hashtag 필터(SQL) → summary 기반 GPT 검색
    async def search_diaries(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
    ) -> list[dict]:
        # 조사 제거 후 2글자 이상인 것만 사용 ("내가"→"내", "언제"는 그대로)
        raw_keywords = [kw.strip() for kw in query.split() if kw.strip()]
        keywords = list({_strip_particle(kw) for kw in raw_keywords if len(_strip_particle(kw)) >= 2})

        # 1단계: hashtags 테이블로 SQL 필터링 (GPT 토큰 소모 없음)
        matched_ids = await self._filter_by_hashtags(db, user_id, keywords)

        # hashtag 매칭 결과가 있으면 그것만, 없으면 최근 30개 summary로 폴백
        if matched_ids:
            stmt = (
                select(DiarySummary)
                .where(
                    DiarySummary.user_id == user_id,
                    DiarySummary.diary_id.in_(matched_ids),
                )
                .order_by(DiarySummary.diary_date.desc())
            )
        else:
            stmt = (
                select(DiarySummary)
                .where(DiarySummary.user_id == user_id)
                .order_by(DiarySummary.diary_date.desc())
                .limit(30)
            )

        result = await db.execute(stmt)
        summaries = result.scalars().all()

        if not summaries:
            return {"answer": "아직 작성된 일기가 없어요.", "results": []}

        # 2단계: 원문 대신 summary만 GPT에 전달
        summary_texts = "\n".join([
            f"[일기 ID: {s.diary_id}] [{s.diary_date}] {s.summary}"
            for s in summaries
        ])

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 사용자의 일기를 검색해주는 친근한 말벗입니다.\n"
                            "사용자가 찾고 싶은 기억을 입력하면, 아래 일기 요약 목록에서 관련 내용을 찾아 구어체로 답변해주세요.\n\n"
                            "검색 시 주의사항:\n"
                            "- '운동 후', '운동하고' 등 간접 표현도 '운동'과 관련된 내용으로 처리하세요.\n"
                            "- 정확한 단어 일치가 아니어도 의미상 관련 있으면 결과로 포함하세요.\n"
                            "- 날짜를 묻는 질문이면 관련 일기가 여러 개여도 모두 포함하세요.\n\n"
                            "답변 형식:\n"
                            "1. 관련 일기가 있으면: 날짜와 내용을 언급하며 친근하게 답변해주세요. "
                            "예) '26년 3월 24일에 VDL V02를 구입하셨네요~'\n"
                            "2. 관련 일기가 없으면: '찾아보았지만 일기에 없는 내용이에요 :)' 라고 답변해주세요.\n\n"
                            "그리고 답변 마지막에 관련 일기 ID를 하이픈 포함 UUID 형식으로 "
                            "'[IDs: uuid1, uuid2]' 형태로 추가해주세요. 없으면 '[IDs: 없음]'으로 표시해주세요.\n\n"
                            f"일기 요약 목록:\n{summary_texts}"
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=400,
            )
            gpt_answer = response.choices[0].message.content.strip()
            logger.debug("[SEARCH] GPT 응답:\n%s", gpt_answer)

            # GPT 응답에서 IDs 파싱 후 원문 조회
            matched_diaries = []
            if "[IDs:" in gpt_answer:
                answer_text = gpt_answer[:gpt_answer.rfind("[IDs:")].strip()
                ids_part = gpt_answer[gpt_answer.rfind("[IDs:") + 5:].strip().rstrip("]").strip()
                logger.debug("[SEARCH] 파싱된 IDs: %s", ids_part)
                if ids_part != "없음":
                    matched_ids = [id.strip() for id in ids_part.split(",")]
                    logger.debug("[SEARCH] DB 조회할 ID 목록: %s", matched_ids)
                    # 문자열 → UUID 변환 (타입 불일치 방지, 잘못된 형식은 skip)
                    matched_uuids = []
                    for id_str in matched_ids:
                        try:
                            matched_uuids.append(uuid.UUID(id_str))
                        except ValueError:
                            logger.debug("[SEARCH] UUID 변환 실패: %s", id_str)
                    diary_stmt = select(Diary).where(
                        Diary.user_id == user_id,
                        Diary.id.in_(matched_uuids),
                    )
                    diary_result = await db.execute(diary_stmt)
                    diaries = diary_result.scalars().all()
                    logger.debug("[SEARCH] DB 조회 결과 %d건", len(diaries))
                    for diary in diaries:
                        matched_diaries.append({
                            "id": str(diary.id),
                            "diary_date": str(diary.diary_date),
                            "title": diary.title,
                            "content": diary.content,
                        })
            else:
                answer_text = gpt_answer
                logger.debug("[SEARCH] GPT 응답에 [IDs:] 없음")

            return {"answer": answer_text, "results": matched_diaries}

        except Exception:
            return {"answer": "검색 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.", "results": []}