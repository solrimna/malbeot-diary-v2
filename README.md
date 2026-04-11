# 하루.commit() - 말벗 AI 일기장

> 음성 입력과 AI 공감 피드백이 결합된 감성 일기 서비스
> 팀 프로젝트(v1) 종료 후 개인 개선 작업 중인 버전입니다. — [원본 저장소](https://github.com/solrimna/malbeot-diary)

**라이브 데모:** https://malbeot.duckdns.org/

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 음성 일기 작성 | Azure STT로 음성을 텍스트로 변환하여 일기 작성 |
| AI 공감 피드백 | 일기 저장 시 GPT 기반 말벗 피드백 자동 생성 (스트리밍) |
| TTS 음성 재생 | OpenAI TTS로 피드백을 말벗 목소리로 재생 |
| 페르소나 커스텀 | Q&A 온보딩으로 나만의 AI 말벗 성격·목소리 설정 |
| 해시태그 자동 생성 | GPT가 일기 내용에서 감정·사건·장소 등 해시태그 추출 |
| AI 일기 검색 | 해시태그 필터 + GPT 자연어 검색으로 과거 일기 탐색 |
| 캘린더 뷰 | 월별 달력으로 일기 기록 조회 |
| 알람 & 리마인더 | 요일 반복 알람 설정, APScheduler로 30초 간격 체크 |
| 웹 푸시 알림 | Service Worker 기반 PWA 푸시 알림 |

자세한 기능 명세는 [docs/features.md](docs/features.md)를 참고해주세요.

---

## 변경 이력

- 2026-04-11 settings.html 신규 생성 — AI 페르소나·알람 좌측 메뉴로 통합
- 2026-04-11 profile.html 나의 현황으로 명칭 변경, 달력만 표시
- 2026-04-11 전 페이지 nav 3항목 통일
- 2026-04-11 config.py extra=ignore 추가 — Docker secrets 환경변수 충돌 방지

---

## 기술 스택

| 분류 | 사용 기술 |
|------|-----------|
| Backend | FastAPI, Uvicorn, SQLAlchemy 2.0 (async), Alembic |
| AI | OpenAI GPT-4o-mini, OpenAI TTS |
| 음성 인식 | Azure Cognitive Services Speech (STT) / Web Speech API |
| Database | PostgreSQL (운영) / SQLite (로컬 개발) |
| Cache | Redis 7 |
| Scheduler | APScheduler 3.10.4 |
| Web Push | pywebpush 2.3.0 |
| Frontend | Vanilla JS (ES6+), Tailwind CSS, Unicorn Studio |
| DevOps | Docker, Docker Compose, Nginx, Let's Encrypt |
| Infra | Terraform, AWS (EC2, RDS), DuckDNS |

---

## 구조도

```
  ┌─────────────────────────────────────────────────────────────┐
  │                        Client (Browser)                      │
  │  index  login  diary_write  diary_read  my-diary  profile   │
  │  settings  persona-onboarding                              │
  │  js/ (api.js · auth.js · diary.js · alarm.js · stt.js)     │
  │  stt.js: Azure STT ← WebSocket / Web Speech API ← 브라우저 │
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
  │             │ │            │ │  - OpenAI (GPT · TTS)       │
  │ users       │ │ 캐시/세션  │ │  - Azure Speech (STT)       │
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
# ── App ──────────────────────────────────────────────
APP_ENV=development
SECRET_KEY=             # python -c "import secrets; print(secrets.token_hex(32))"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── Database ─────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./malbeot.db   # 로컬 개발 (SQLite)
# DATABASE_URL=postgresql+asyncpg://user:pw@host:5432/malbeot  # 운영

# ── Redis (선택) ──────────────────────────────────────
USE_REDIS=False
REDIS_URL=redis://localhost:6379/0

# ── OpenAI ───────────────────────────────────────────
OPENAI_API_KEY=         # https://platform.openai.com/api-keys

# ── Azure Speech (STT) ───────────────────────────────
AZURE_SPEECH_KEY=       # https://portal.azure.com → Speech Services
AZURE_SPEECH_REGION=koreacentral

# ── Web Push (VAPID) ─────────────────────────────────
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_CLAIMS_SUB=       # mailto:your@email.com
```

### 3. 의존성 설치

```bash
pip install uv
uv pip install -r requirements.txt
```

### 4. DB 마이그레이션

```bash
alembic upgrade head
```

### 5. 서버 실행

```bash
uvicorn app.main:app --reload
```

브라우저에서 `http://localhost:8000` 접속

---

## Docker로 실행

```bash
docker compose up --build
```

---

## API 키 발급 안내

### Azure Speech API Key

1. [Azure Portal](https://portal.azure.com) 접속
2. 리소스 만들기 → Speech Services 검색 및 생성
   - 가격 책정: F0 (무료, 월 5시간)
   - 리전: Korea Central
3. 리소스 → 키 및 엔드포인트에서 키 복사
4. `.env` 파일에 추가

### VAPID Key (웹 푸시 알림)

```bash
python -c "from pywebpush import Vapid; v = Vapid(); v.generate_keys(); print('Public:', v.public_key); print('Private:', v.private_key)"
```

생성된 공개키/개인키를 `.env`의 `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY`에 입력하세요.

---

## 문서

| 문서 | 내용 |
|------|------|
| [docs/features.md](docs/features.md) | 전체 기능 명세 및 API 엔드포인트 |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Git 작업 가이드 및 브랜치 전략 |

---
