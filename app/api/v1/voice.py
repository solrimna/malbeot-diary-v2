# 담당: 나 (STT/TTS/GPT 스트리밍 파이프라인)
from fastapi import APIRouter

router = APIRouter()


# TODO: POST /stt         - 음성 파일 → 텍스트 (Google STT)
# TODO: POST /tts         - 텍스트 → 음성 파일 (Google TTS)
# TODO: POST /tts/stream  - GPT 응답 스트리밍 → TTS 파이프라인
