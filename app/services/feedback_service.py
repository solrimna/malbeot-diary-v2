# 담당 : A팀원 유가영
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import logging
from app.models.ai_feedback import AiFeedback
from app.models.diary_summary import DiarySummary
from app.services.gpt_service import GPTService
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# 교수님 피드백 반영: 페르소나별 말투 가이드라인
PERSONA_PROMPTS = {
    "empathy": (
        "당신은 따뜻하고 공감 능력이 뛰어난 말벗입니다. "
        "사용자의 감정을 먼저 읽고, '그랬구나', '많이 힘들었겠다' 같은 공감 표현을 자주 사용하세요. "
        "조언보다는 감정을 받아주는 데 집중하세요. 2~3문장으로 짧게 답하세요."
    ),
    "advice": (
        "당신은 현실적이고 솔직한 조언을 해주는 말벗입니다. "
        "사용자의 상황을 파악하고 구체적인 행동 방안을 제안하세요. "
        "부드럽지만 직접적으로 이야기하세요. 2~3문장으로 짧게 답하세요."
    ),
    "info": (
        "당신은 지식이 풍부하고 차분한 정보 제공형 말벗입니다. "
        "사용자의 일기에서 관련된 유용한 정보나 관점을 제공하세요. "
        "객관적이고 명확하게 이야기하세요. 2~3문장으로 짧게 답하세요."
    ),
}
# "custom"은 PERSONA_PROMPTS에서 제외
# preset_type="custom"일 때는 custom_description을 직접 사용해야 하므로
# 여기 있으면 elif custom_description 분기에 절대 도달하지 못함

DEFAULT_PROMPT = PERSONA_PROMPTS["empathy"]


def build_system_prompt(
    persona_name: str,
    preset_type: str | None,
    custom_description: str | None,
    persona_memory: str | None = None,
    memory_context: str | None = None,
) -> str:
    if preset_type and preset_type in PERSONA_PROMPTS:
        base = PERSONA_PROMPTS[preset_type]
    elif custom_description:
        # 페르소나 설명에서 말투 감지 후 강제 적용
        if "반말로 이야기해요" in custom_description:
            speech_rule = "반드시 반말로만 대화하세요. 존댓말을 절대 섞지 마세요."
        elif "존댓말로 이야기해요" in custom_description:
            speech_rule = "반드시 존댓말로만 대화하세요. 반말을 절대 섞지 마세요."
        else:
            speech_rule = "반말 또는 존댓말 중 하나를 선택해 일관되게 사용하세요. 절대 섞지 마세요."
        base = f"당신은 {custom_description} 성격의 말벗입니다. {speech_rule} 2~3문장으로 짧게 답하세요."
    else:
        base = DEFAULT_PROMPT

    prompt = f"당신의 이름은 '{persona_name}'입니다. " + base

    if persona_memory:
        prompt += f"\n\n[반드시 기억할 것]\n{persona_memory}"

    if memory_context:
        prompt += (
            f"\n\n[이 사용자의 최근 기록]\n{memory_context}\n"
            "위 기록을 참고해 사용자를 더 잘 이해하고 공감해주세요. 단, 기록을 직접 언급하거나 요약하지 마세요."
        )

    return prompt


class FeedbackService:
    def __init__(self):
        self.gpt = GPTService()

    async def _get_memory_context(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        exclude_diary_id: uuid.UUID,
    ) -> str | None:
        """최근 7개 일기 요약을 메모리 컨텍스트 문자열로 반환"""
        stmt = (
            select(DiarySummary)
            .where(
                DiarySummary.user_id == user_id,
                DiarySummary.diary_id != exclude_diary_id,
            )
            .order_by(DiarySummary.diary_date.desc())
            .limit(7)
        )
        result = await db.execute(stmt)
        summaries = result.scalars().all()

        if not summaries:
            return None

        lines = [
            f"- ({s.diary_date.strftime('%Y-%m-%d')}) {s.summary}"
            for s in reversed(summaries)  # 오래된 순 → 최신 순 정렬
        ]
        return "\n".join(lines)

    # ── 스트리밍 피드백 생성
    async def stream_feedback(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        diary_id: uuid.UUID,
        diary_content: str,
        persona_name: str,
        preset_type: str | None,
        custom_description: str | None,
        persona_memory: str | None = None,
    ) -> AsyncGenerator[str, None]:
        memory_context = await self._get_memory_context(db, user_id, diary_id)
        system_prompt = build_system_prompt(persona_name, preset_type, custom_description, persona_memory, memory_context)
        logger.debug("[SYSTEM PROMPT - stream]\n%s", system_prompt)
        async for sentence in self.gpt.stream_feedback(
            diary_content=diary_content,
            persona_prompt=system_prompt,
        ):
            yield sentence

    # ── 피드백 생성 & DB 저장
    async def create_feedback(
        self,
        db: AsyncSession,
        diary_id: uuid.UUID,
        user_id: uuid.UUID,
        persona_id: uuid.UUID | None,
        diary_content: str,
        persona_name: str,
        preset_type: str | None,
        custom_description: str | None,
        persona_memory: str | None = None,
    ) -> AiFeedback:
        existing = await self.get_feedback(db, diary_id)
        if existing:
            return existing

        memory_context = await self._get_memory_context(db, user_id, diary_id)
        system_prompt = build_system_prompt(persona_name, preset_type, custom_description, persona_memory, memory_context)
        logger.debug("[SYSTEM PROMPT - create]\n%s", system_prompt)

        # GPT 스트리밍 결과 모아서 저장
        full_text = ""
        async for sentence in self.gpt.stream_feedback(
            diary_content=diary_content,
            persona_prompt=system_prompt,
        ):
            full_text += sentence + " "

       # 페르소나 없으면 default 페르소나 조회 또는 생성
        if not persona_id:
            from app.models.persona import Persona
            stmt = select(Persona).where(
                Persona.user_id == user_id,
                Persona.name == "기본 말벗",
            )
            result = await db.execute(stmt)
            default_persona = result.scalar_one_or_none()

            if not default_persona:
                default_persona = Persona(
                    user_id=user_id,
                    name="기본 말벗",
                    preset_type="empathy",
                )
                db.add(default_persona)
                await db.flush()

            persona_id = default_persona.id

        feedback = AiFeedback(
            diary_id=diary_id,
            persona_id=persona_id,
            feedback_text=full_text.strip(),
            feedback_type=preset_type or "empathy",
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    # ── 저장된 피드백 조회
    async def get_feedback(
        self,
        db: AsyncSession,
        diary_id: uuid.UUID,
    ) -> AiFeedback | None:
        stmt = select(AiFeedback).where(AiFeedback.diary_id == diary_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()