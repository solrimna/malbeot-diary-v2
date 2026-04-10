# 하루.commit() - 말벗 AI 일기장

> 음성 입력과 AI 공감 피드백이 결합된 감성 일기 서비스

**라이브 데모:** https://malbeot.duckdns.org/

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 음성 일기 작성 | Azure STT로 음성을 텍스트로 변환하여 일기 작성 |
| AI 공감 피드백 | 일기 저장 시 GPT 기반 말벗 피드백 자동 생성 |
| TTS 음성 재생 | OpenAI TTS로 피드백을 말벗 목소리로 재생 |
| 페르소나 커스텀 | Q&A 온보딩으로 나만의 AI 말벗 성격·목소리 설정 |
| 해시태그 자동 생성 | GPT가 일기 내용에서 감정·사건·장소 등 해시태그 추출 |
| AI 일기 검색 | 해시태그 필터 + GPT 자연어 검색으로 과거 일기 탐색 |
| 캘린더 뷰 | 월별 달력으로 일기 기록 조회 |

---

## 기술 스택

| 분류 | 사용 기술 |
|------|-----------|
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| AI | OpenAI GPT-4o-mini, OpenAI TTS, Azure Speech STT |
| Database | PostgreSQL, Redis |
| Infra | Docker Compose, Nginx, Let's Encrypt |
| Frontend | Vanilla JS, HTML/CSS |

---

## 구조도
```
  ┌─────────────────────────────────────────────────────────────┐
  │                        Client (Browser)                      │
  │  index  login  diary_write  diary_read  my-diary  profile   │
  │  ai-persona  persona-onboarding                             │
  │  js/ (api.js · auth.js · diary.js · alarm.js · stt.js)     │
  │  sw.js (Service Worker / Web Push)                          │
  └────────────────────────┬────────────────────────────────────┘
                           │ HTTPS
  ┌────────────────────────▼────────────────────────────────────┐
  │                     nginx (443/80)                           │
  │  - HTTP → HTTPS 리다이렉트                                   │
  │  - WebSocket Upgrade 헤더 처리                               │
  │  - Let's Encrypt SSL                                         │
  └────────────────────────┬────────────────────────────────────┘
                           │ proxy_pass :8000
  ┌────────────────────────▼────────────────────────────────────┐
  │                   FastAPI app (:8000)                        │
  │                                                             │
  │  main.py                                                    │
  │  ├── lifespan: DB 초기화 + 알람 스케줄러 시작/종료           │
  │  ├── /api/v1 ── router.py                                   │
  │  │   ├── /auth      → auth.py      → auth_service.py       │
  │  │   ├── /diaries   → diary.py     → diary_service.py      │
  │  │   ├── /personas  → persona.py   → gpt_service.py        │
  │  │   ├── /feedback  → feedback.py  → feedback_service.py   │
  │  │   ├── /voice     → voice.py     → stt/tts_service.py    │
  │  │   ├── /alarms    → alarm.py     → alarm_service.py      │
  │  │   └── /search    → search.py    → search_service.py     │
  │  └── /  (StaticFiles → frontend/)                          │
  └──────┬──────────────┬───────────────┬───────────────────────┘
         │              │               │
  ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────────────────────┐
  │ PostgreSQL  │ │   Redis    │ │   External APIs             │
  │             │ │            │ │  - OpenAI (GPT · STT · TTS) │
  │ users       │ │ 캐시/세션  │ │  - Google TTS               │
  │ diaries     │ │            │ │  - Web Push (pywebpush)     │
  │ personas    │ └────────────┘ └────────────────────────────┘
  │ ai_feedbacks│
  │ alarms      │
  │ push_subs   │
  └─────────────┘
```
---

## 시작하기

### 1. 저장소 clone
```bash
git clone https://github.com/solrimna/malbeot-diary.git
cd malbeot-diary
```

### 2. 환경변수 세팅
```bash
copy .env.example .env
```

`.env` 파일을 열어서 아래 값들을 채워주세요.
```dotenv
SECRET_KEY=             # 랜덤 키 생성: python -c "import secrets; print(secrets.token_hex(32))"
OPENAI_API_KEY=         # https://platform.openai.com/api-keys
AZURE_SPEECH_KEY=       # https://portal.azure.com → Speech Services
AZURE_SPEECH_REGION=koreacentral
```

### 3. 의존성 설치
```bash
pip install uv
uv pip install -r requirements.txt
```

### 4. 서버 실행
```bash
uvicorn app.main:app --reload
```

---

## 문서

트러블슈팅, 아키텍처 등 상세 문서는 [GitHub Wiki](../../wiki)를 참고해주세요.

---

### Azure Speech API Key 발급
1. [Azure Portal](https://portal.azure.com) 접속
2. 리소스 만들기 → Speech Services 검색 및 생성
   - 가격 책정: F0 (무료, 월 5시간)
   - 리전: Korea Central
3. 리소스 → 키 및 엔드포인트에서 키 복사
4. `.env` 파일에 추가

---

## Git 작업 가이드

자세한 내용은 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)를 참고해주세요.
