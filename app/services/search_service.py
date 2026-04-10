# 담당 : A팀원 유가영
# 2026-03-31 나솔림 수정 (검색 성능 개선)
# 2026-04-01 나솔림 수정 (부정/카운팅 쿼리 처리)
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
#
# [부정/카운팅 쿼리 처리] _search_negation()
# - "운동 안 한 날", "몇 번 빠졌지" 등 부정/카운팅 의도 감지 → 별도 흐름
# - 날짜 범위 지정 시 해당 기간만 조회, 없으면 최근 90일
# - 답변 앞에 "(최근 N일 / 일기를 작성한 날 기준)" 참조 범위 노출
#
# ★ GPT 프롬프트 수정 시 주의사항 ★
#
# [일반 검색 - _ask_gpt()]
# - GPT가 "기억", "찾아줘" 등 메타 표현을 키워드로 오인하는 문제가 있었음
#   → keyword_hint에 "참고 키워드(엄격히 일치하지 않아도 됨)" 표기로 강제성 제거
# - "운동 간 날" vs "운동을 하고" 처럼 표현 방식이 달라도 같은 의미로 판단하도록
#   "의미가 같으면 반드시 관련 있는 것으로 판단하세요" 문구 필수 유지
# - "'없음'으로 판단하기 전에 의미상 연관성을 한 번 더 검토하세요" 문구 필수 유지
#
# [부정/카운팅 검색 - _search_negation()]
# - GPT에게 카운팅을 맡기면 오답률이 높음 (테스트 결과 "2일"을 "3일", "4일"로 답변)
#   → 서버에서 [활동기록: 있음/없음] 레이블을 직접 계산해 summary_texts에 포함
#   → 카운팅 결과(날짜 목록·건수)도 [사전 분석] 블록으로 summary_texts 상단에 명시
#   → GPT는 숫자를 직접 세지 않고 사전 분석 결과를 읽어 답변 형식만 만들도록 유도
# - "[운동기록: 없음]"인 날이 있으면 "기록하지 않으셨다면 실제와 다를 수 있어요" 안내
#   (일기에 쓰지 않은 날 = 운동했어도 없음으로 표시될 수 있음을 사용자에게 고지)
# - 없음 판정 기준:
#   A. "{활동}안함" 태그 보유 → 일기에 명시적으로 못 했다고 적은 날
#   B. 관련 태그 아예 없음  → 언급 자체를 안 한 날 (실제와 다를 수 있음)

import logging
import re
import uuid
from datetime import date, timedelta

from openai import AsyncOpenAI
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.diary import Diary
from app.models.diary_summary import DiarySummary
from app.models.hashtag import DiaryHashtag, Hashtag

logger = logging.getLogger(__name__)
settings = get_settings()
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

DEFAULT_NEGATION_DAYS = 90  # 날짜 범위 미지정 시 기본 참조 범위

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


# 부정/카운팅 의도 감지 패턴
_NEGATION_PATTERNS = re.compile(
    r"(안\s|못\s|안한|못한|안\s*간|못\s*간|안간|못간|하지\s*않|빠진|빠졌|없는|없었|안\s*갔|못\s*갔|몇\s*일|몇\s*번|몇\s*번이나|횟수|빠뜨린)"
)

def _detect_negation_intent(query: str) -> bool:
    return bool(_NEGATION_PATTERNS.search(query))


def _extract_date_range(query: str, today: date) -> tuple[date | None, date | None, str]:
    """
    쿼리에서 날짜 범위 추출.
    반환: (from_date, to_date, 사용자에게 보여줄 범위 레이블)
    날짜 범위를 찾지 못하면 (None, None, "") 반환
    """
    # 이번달
    if re.search(r"이번\s*달|이번\s*월", query):
        start = today.replace(day=1)
        return start, today, f"{start.strftime('%Y년 %m월')} 기준"

    # 지난달
    if re.search(r"지난\s*달|저번\s*달|지난\s*월", query):
        first_this_month = today.replace(day=1)
        end = first_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return start, end, f"{start.strftime('%Y년 %m월')} 기준"

    # 이번주
    if re.search(r"이번\s*주", query):
        start = today - timedelta(days=today.weekday())
        return start, today, f"이번 주({start.strftime('%m/%d')}~{today.strftime('%m/%d')}) 기준"

    # 지난주
    if re.search(r"지난\s*주|저번\s*주", query):
        this_week_start = today - timedelta(days=today.weekday())
        end = this_week_start - timedelta(days=1)
        start = end - timedelta(days=6)
        return start, end, f"지난 주({start.strftime('%m/%d')}~{end.strftime('%m/%d')}) 기준"

    # 올해
    if re.search(r"올해|금년", query):
        start = today.replace(month=1, day=1)
        return start, today, f"{today.year}년 기준"

    # 작년
    if re.search(r"작년|지난\s*해", query):
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
        return start, end, f"{today.year - 1}년 기준"

    # N월 (예: 3월, 12월)
    m = re.search(r"(\d{1,2})\s*월", query)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            year = today.year if month <= today.month else today.year - 1
            start = date(year, month, 1)
            if month == 12:
                end = date(year, 12, 31)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            return start, end, f"{year}년 {month}월 기준"

    return None, None, ""


class SearchService:

    async def _filter_by_hashtags(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        keywords: list[str],
    ) -> list[uuid.UUID]:
        """쿼리 키워드와 매칭되는 diary_id 목록 반환 (hashtags 테이블 기준, SQL only)"""
        conditions = [Hashtag.name == kw for kw in keywords]
        stmt = (
            select(DiaryHashtag.diary_id)
            .join(Hashtag, DiaryHashtag.hashtag_id == Hashtag.id)
            .where(Hashtag.user_id == user_id, or_(*conditions))
            .distinct()
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _get_hashtags_for_diaries(
        self,
        db: AsyncSession,
        diary_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, list[str]]:
        """diary_id → 해시태그 이름 목록 매핑"""
        if not diary_ids:
            return {}
        stmt = (
            select(DiaryHashtag.diary_id, Hashtag.name)
            .join(Hashtag, DiaryHashtag.hashtag_id == Hashtag.id)
            .where(DiaryHashtag.diary_id.in_(diary_ids))
        )
        result = await db.execute(stmt)
        hashtag_map: dict[uuid.UUID, list[str]] = {}
        for diary_id, name in result.all():
            hashtag_map.setdefault(diary_id, []).append(name)
        return hashtag_map

    # ── 일기 검색: hashtag 필터(SQL) → summary 기반 GPT 검색
    async def search_diaries(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
    ) -> list[dict]:

        # 부정/카운팅 의도 감지 → 별도 흐름
        if _detect_negation_intent(query):
            return await self._search_negation(db, user_id, query)

        # 조사 제거 후 2글자 이상인 것만 사용 ("내가"→"내", "언제"는 그대로)
        raw_keywords = [kw.strip() for kw in query.split() if kw.strip()]
        keywords = list({_strip_particle(kw) for kw in raw_keywords if len(_strip_particle(kw)) >= 2})

        # 부정 감지 시 "{키워드}안함" 태그도 함께 검색
        if _detect_negation_intent(query):
            keywords += [f"{kw}안함" for kw in keywords]

        # 1단계: hashtags 테이블로 SQL 필터링 (GPT 토큰 소모 없음)
        matched_ids = await self._filter_by_hashtags(db, user_id, keywords)
        logger.info("[SEARCH] 키워드: %s | matched_ids: %s", keywords, matched_ids)

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
        logger.info("[SEARCH] summaries: %s", [(str(s.diary_id), s.summary) for s in summaries])
        summary_texts = "\n".join([
            f"[일기 ID: {s.diary_id}] [{s.diary_date}] {s.summary}"
            for s in summaries
        ])

        return await self._ask_gpt(query, summary_texts, db, user_id, keywords=keywords)

    async def _search_negation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
    ) -> dict:
        """부정/카운팅 쿼리 처리: 날짜 범위 필터 + 해시태그 포함 summary → GPT"""
        today = date.today()
        date_from, date_to, range_label = _extract_date_range(query, today)

        if date_from and date_to:
            stmt = (
                select(DiarySummary)
                .where(
                    DiarySummary.user_id == user_id,
                    DiarySummary.diary_date >= date_from,
                    DiarySummary.diary_date <= date_to,
                )
                .order_by(DiarySummary.diary_date.asc())
            )
            ref_label = range_label
        else:
            cutoff = today - timedelta(days=DEFAULT_NEGATION_DAYS)
            stmt = (
                select(DiarySummary)
                .where(
                    DiarySummary.user_id == user_id,
                    DiarySummary.diary_date >= cutoff,
                )
                .order_by(DiarySummary.diary_date.asc())
            )
            ref_label = f"최근 {DEFAULT_NEGATION_DAYS}일"

        result = await db.execute(stmt)
        summaries = result.scalars().all()

        if not summaries:
            return {"answer": f"{ref_label} 내에 작성된 일기가 없어요.", "results": []}

        # 해시태그 정보 조회
        diary_ids = [s.diary_id for s in summaries]
        hashtag_map = await self._get_hashtags_for_diaries(db, diary_ids)

        # 쿼리에서 주제 키워드 추출 (부정·조사·메타 표현 제외)
        _META = {"몇", "일", "번", "날", "때", "횟수", "얼마나", "몇번", "몇일"}
        raw_kws = [_strip_particle(kw) for kw in query.split() if kw.strip()]
        subject_kws = [kw for kw in raw_kws
                       if len(kw) >= 2 and kw not in _META
                       and not _NEGATION_PATTERNS.search(kw)]

        # 각 일기에 주제 활동 기록 여부 표시 (exact match)
        def _activity_status(tags: set[str], subjects: list[str]) -> str:
            for subj in subjects:
                if subj in tags:
                    return "있음"
            return "없음"

        summary_lines = []
        for s in summaries:
            tags = set(hashtag_map.get(s.diary_id, []))
            record_note = ""
            if subject_kws:
                status = _activity_status(tags, subject_kws)
                record_note = f"[{'/'.join(subject_kws)}기록: {status}] "
            summary_lines.append(
                f"[일기 ID: {s.diary_id}] [{s.diary_date}] "
                f"{record_note}"
                f"[태그: {', '.join(tags) or '없음'}] "
                f"{s.summary}"
            )
        # 없음 날짜를 서버에서 미리 계산 → GPT가 직접 세지 않도록
        precomputed_note = ""
        if subject_kws:
            no_record = [
                str(s.diary_date) for s in summaries
                if _activity_status(set(hashtag_map.get(s.diary_id, [])), subject_kws) == "없음"
            ]
            if no_record:
                precomputed_note = (
                    f"[사전 분석] '{'/'.join(subject_kws)}' 기록이 없는 날: "
                    f"총 {len(no_record)}일 ({', '.join(no_record)})\n"
                    f"※ 위 숫자와 날짜는 서버가 계산한 확정값입니다. 직접 세거나 추론하지 마세요.\n\n"
                )

        summary_texts = precomputed_note + "\n".join(summary_lines)
        logger.info("[SEARCH][NEGATION] subject_kws=%s\n%s", subject_kws, summary_texts)

        result = await self._ask_gpt(query, summary_texts, db, user_id, ref_label=ref_label)
        # 참조 범위를 답변 앞에 노출
        result["answer"] = f"({ref_label} / 일기를 작성한 날 기준으로 답변했어요)\n\n{result['answer']}"
        return result

    async def _ask_gpt(
        self,
        query: str,
        summary_texts: str,
        db: AsyncSession,
        user_id: uuid.UUID,
        ref_label: str | None = None,
        keywords: list[str] | None = None,
    ) -> dict:
        keyword_hint = ""
        if keywords:
            keyword_hint = f"참고 키워드(엄격히 일치하지 않아도 됨): {', '.join(keywords)}\n\n"

        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 사용자의 일기를 검색해주는 친근한 말벗입니다.\n"
                            "사용자가 찾고 싶은 기억을 입력하면, 아래 일기 요약 목록에서 관련 내용을 찾아 구어체로 답변해주세요.\n\n"
                            f"{keyword_hint}"
                            "검색 시 주의사항:\n"
                            "- 사용자가 표현한 방식과 일기에 기록된 방식이 다를 수 있습니다. 의미가 같으면 반드시 관련 있는 것으로 판단하세요.\n"
                            "  예) '운동 간 날' → '운동을 하고', '운동했다' / '밥 먹었어' → '식사를 했다'\n"
                            "- '없음'으로 판단하기 전에 의미상 연관성을 한 번 더 검토하세요.\n"
                            "- '기억', '찾아줘', '알려줘' 등 검색 요청 표현 자체는 키워드로 취급하지 마세요.\n"
                            "- 날짜를 묻는 질문이면 관련 일기가 여러 개여도 모두 포함하세요.\n"
                            "- 각 일기에 '[운동기록: 있음/없음]' 형태로 서버가 사전 분석한 결과가 포함되어 있습니다. "
                            "카운팅·날짜 질문은 이 표시를 기준으로 정확히 답변하세요.\n"
                            "- '없음'인 날이 있다면 답변 마지막에 '기록하지 않으셨다면 실제와 다를 수 있어요 :)'를 덧붙이세요.\n"
                            "- 횟수/카운팅 질문은 조건에 맞는 일기 수를 세어 답변해주세요.\n\n"
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
            logger.info("[SEARCH] GPT 응답:\n%s", gpt_answer)

            # GPT 응답에서 IDs 파싱 후 원문 조회
            matched_diaries = []
            if "[IDs:" in gpt_answer:
                answer_text = gpt_answer[:gpt_answer.rfind("[IDs:")].strip()
                ids_part = gpt_answer[gpt_answer.rfind("[IDs:") + 5:].strip().rstrip("]").strip()
                logger.debug("[SEARCH] 파싱된 IDs: %s", ids_part)
                if ids_part != "없음":
                    matched_ids = [id.strip() for id in ids_part.split(",")]
                    logger.debug("[SEARCH] DB 조회할 ID 목록: %s", matched_ids)
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


search_service = SearchService()
