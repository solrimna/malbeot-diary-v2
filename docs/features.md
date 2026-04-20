# 하루.commit() — 기능 명세서

AI 기반 감성 일기 서비스. 음성 입력, AI 피드백, 맞춤형 말벗 페르소나를 결합한 웹 애플리케이션입니다.

---

## 목차

1. [인증 / 사용자 관리](#1-인증--사용자-관리)
2. [일기 CRUD](#2-일기-crud)
3. [AI 피드백](#3-ai-피드백)
4. [말벗 페르소나](#4-말벗-페르소나)
5. [음성 입출력 (STT / TTS)](#5-음성-입출력-stt--tts)
6. [해시태그 자동 생성](#6-해시태그-자동-생성)
7. [AI 기억 검색](#7-ai-기억-검색)
8. [알람 & 리마인더](#8-알람--리마인더)
9. [웹 푸시 알림 (PWA)](#9-웹-푸시-알림-pwa)
10. [프론트엔드 페이지](#10-프론트엔드-페이지)

---

## 1. 인증 / 사용자 관리

**인증**

| 항목 | 내용 |
|------|------|
| 회원가입 | `POST /api/v1/auth/register` |
| 로그인 | `POST /api/v1/auth/login` — JWT 액세스 토큰 발급 |
| 로그아웃 | `POST /api/v1/auth/logout` |

**내 계정 관리**

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/v1/users/me` | 내 프로필 조회 |
| `PATCH` | `/api/v1/users/me` | 닉네임 · 비밀번호 수정 |
| `DELETE` | `/api/v1/users/me` | 회원 탈퇴 (관련 데이터 CASCADE 삭제) |

- JWT 기반 무상태 인증 (기본 만료 60분)
- bcrypt 비밀번호 해싱
- 아이디(username) 대소문자 구분 없이 처리 — 가입·로그인 시 `field_validator`로 즉시 소문자 변환, 대소문자 중복 가입 방지
- 사용자 프로필: 닉네임, 프로필 이미지 URL
- DB 확장 (소셜 로그인 대비): `email`, `auth_provider`, `social_id` 컬럼 추가 (마이그레이션 `005`)

**이메일 인증 (회원가입 — 매직 링크)**

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/v1/auth/register` | 회원가입 → 인증 메일 자동 발송 |
| `GET` | `/api/v1/auth/verify-email` | 매직 링크 클릭 → 이메일 인증 완료 |

- 회원가입 직후 Brevo 트랜잭션 메일로 인증 링크 발송
- 링크에 서명된 단기 토큰 포함 (만료: 24시간)
- 미인증 계정은 로그인 시 안내 메시지 표시 (또는 로그인 차단 — 정책 결정 후 반영)
- 이메일 인증 완료 시 `users.is_verified = true` 업데이트

**비밀번호 분실 & 재설정**

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/v1/auth/forgot-password` | 이메일 입력 → 재설정 링크 발송 |
| `POST` | `/api/v1/auth/reset-password` | 토큰 + 새 비밀번호 → 비밀번호 변경 |

- Brevo 트랜잭션 메일로 재설정 링크 발송
- 링크에 서명된 단기 토큰 포함 (만료: 1시간)
- 토큰 1회 사용 후 무효화
- 메일 발송 서비스: **Brevo** (`sib-api-v3-sdk` 또는 Brevo REST API)

---

## 2. 일기 CRUD

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/v1/diaries` | 목록 조회 (해시태그 · 날짜 범위 · 페이지네이션 필터) |
| `POST` | `/api/v1/diaries` | 일기 작성 — 피드백 · 해시태그 자동 생성 트리거 |
| `GET` | `/api/v1/diaries/{id}` | 단건 조회 |
| `PATCH` | `/api/v1/diaries/{id}` | 수정 — 피드백 재생성 포함 |
| `DELETE` | `/api/v1/diaries/{id}` | 삭제 |
| `GET` | `/api/v1/diaries/{id}/hashtags` | 해당 일기의 해시태그 조회 |
| `DELETE` | `/api/v1/diaries/{id}/hashtags/{tag}` | 해시태그 개별 삭제 |

**일기 메타데이터:** 감정(emotion), 날씨(weather), 일기 날짜, 입력 방식(text / voice / mixed), 오디오 파일 URL

---

## 3. AI 피드백

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/v1/feedback/{id}/stream` | 스트리밍 피드백 생성 (실시간 출력) |
| `POST` | `/api/v1/feedback/{id}` | 피드백 생성 후 DB 저장 |
| `PUT` | `/api/v1/feedback/{id}/regenerate` | 피드백 재생성 |
| `GET` | `/api/v1/feedback/{id}` | 저장된 피드백 조회 |

**피드백 스타일 (preset_type):**

| 타입 | 설명 |
|------|------|
| `empathy` | 공감 · 감정 지지 |
| `advice` | 실용적 조언 제공 |
| `info` | 사실 기반 정보 전달 |
| `custom` | 온보딩 Q&A로 생성된 맞춤 페르소나 |

- GPT-4o-mini 기반, 2~3문장 응답
- 과거 7개 일기를 메모리 컨텍스트로 활용
- 일기 1건당 피드백 1건 (수정 시 자동 업데이트)
- 스트리밍으로 첫 문장 즉시 표시 (체감 응답 속도 개선)

---

## 4. 말벗 페르소나

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/v1/personas` | 목록 조회 (최초 호출 시 프리셋 3종 자동 생성) |
| `POST` | `/api/v1/personas` | 페르소나 생성 (생성 시 활성화, 기존 페르소나 비활성화) |
| `PATCH` | `/api/v1/personas/{id}` | 속성 수정 |
| `DELETE` | `/api/v1/personas/{id}` | 삭제 |
| `POST` | `/api/v1/personas/onboarding` | Q&A 기반 맞춤 페르소나 생성 |

**페르소나 속성:** 이름, 성격 설명, TTS 목소리(alloy · nova · echo · fable · onyx · shimmer), 아바타 이미지, 기억 메모(memory)

- 사용자당 활성 페르소나는 항상 1개
- GPT가 온보딩 Q&A 답변을 바탕으로 성격 설명 자동 생성

---

## 5. 음성 입출력 (STT / TTS)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/v1/voice/stt` | 음성 파일 → 텍스트 변환 |
| `WebSocket` | `/api/v1/voice/ws/stt` | 실시간 스트리밍 STT |
| `POST` | `/api/v1/voice/tts` | 텍스트 → 음성 파일 생성 |
| `POST` | `/api/v1/voice/tts/stream` | TTS 스트리밍 파이프라인 |
| `GET` | `/api/v1/voice/tts/stats` | TTS 캐시 통계 조회 |

**STT:** Azure Cognitive Services — webm/opus · wav · mp4 · mpeg 지원 (최대 10MB)  
**TTS:** OpenAI TTS — 6가지 목소리, Redis 캐싱(선택)

---

## 6. 해시태그 자동 생성

- 일기 작성 · 내용 수정 시 GPT가 5~7개 태그 자동 추출
- 추출 카테고리: 느낌 / 사건 / 장소 / 사람 / 소재
- 부정 표현 처리: "운동 못했어" → `#운동안함`
- 사용자가 개별 태그 수동 삭제 가능

---

## 7. AI 기억 검색

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `POST` | `/api/v1/search` | 자연어로 일기 검색 |

- 자연어 쿼리 예시: "친구랑 카페 갔던 날", "운동 안 한 날이 몇 번이야?"
- **일반 검색:** 해시태그 SQL 필터 → GPT 의미 기반 매칭 (토큰 절약)
- **부정/카운팅 쿼리 감지:** 날짜 범위 기반 집계 응답
- 기본 탐색 범위: 최근 90일 (쿼리에 날짜 명시 시 해당 기간)
- 검색 결과: 일기 발췌 + GPT 요약 답변

---

## 8. 알람 & 리마인더

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/v1/alarms` | 알람 목록 조회 |
| `POST` | `/api/v1/alarms` | 알람 생성 (중복 검사 포함) |
| `PUT` | `/api/v1/alarms/{id}` | 알람 수정 |
| `DELETE` | `/api/v1/alarms/{id}` | 알람 삭제 |
| `GET` | `/api/v1/alarms/due` | 현재 시각 기준 만료 알람 조회 |
| `GET` | `/api/v1/alarms/test` | 알람 매칭 로직 테스트 |

- HH:MM 형식 시간 설정, 요일 반복 지정 (MON ~ SUN)
- 활성/비활성 토글
- 동일 시간 + 겹치는 요일 중복 생성 방지
- APScheduler cron 트리거로 정시 발송 (기존 30초 폴링 방식에서 변경)

---

## 9. 웹 푸시 알림 (PWA)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| `GET` | `/api/v1/alarms/push/public-key` | VAPID 공개키 조회 |
| `POST` | `/api/v1/alarms/push/subscribe` | 푸시 구독 등록 |

- Service Worker(`sw.js`)로 PWA 오프라인 지원
- pywebpush 기반 서버 → 브라우저 푸시 전송
- 구독 정보 DB(`push_subscriptions`) 저장

---

## 10. 프론트엔드 페이지

| 페이지 | 파일 | 설명 |
|--------|------|------|
| 랜딩 | `index.html` | Unicorn Studio 애니메이션 배경, 로그인/회원가입 진입 |
| 로그인 | `login.html` | 인증 폼 |
| 일기 작성 | `diary_write.html` | 음성 입력, 감정/날씨 선택, 실시간 STT |
| 일기 읽기 | `diary_read.html` | 일기 + AI 피드백 + TTS 재생 |
| 내 일기 | `my-diary.html` | 책장 뷰, 해시태그 필터, AI 기억 검색 |
| 나의 현황 | `profile.html` | 월별 달력으로 일기 기록 확인 |
| 내 프로필 | `my_profile.html` | 닉네임·비밀번호 수정, 로그아웃, 회원 탈퇴 |
| 설정 | `settings.html` | AI 페르소나 관리 + 알람 설정 (좌측 메뉴 탭) |
| 온보딩 | `persona-onboarding.html` | 맞춤 페르소나 생성 Q&A |

**공통 컴포넌트**

- `js/nav.js` — `<app-nav>` Web Component: 일기 작성하기 / 나의 일기장 / AI로 기억 찾기 / 프로필 아이콘(드롭다운: 닉네임 표시, 프로필·나의 현황·설정·로그아웃)
- `js/auth-guard.js` — 보호 페이지 진입 시 렌더링 전 JWT 토큰 검증 → 미인증 시 로그인 페이지 리다이렉트 (깜빡임 제거)
- `js/search.js` — AI 기억 검색 모달 (IIFE 방식, 모든 보호 페이지에서 공유)
- `js/particles.js` — tsParticles 별 파티클 배경 (전 페이지 공통 적용, Unicorn Studio 대체)

---

## 기술 스택 요약

| 분류 | 기술 |
|------|------|
| 백엔드 | FastAPI 0.115, Uvicorn, SQLAlchemy 2.0 (async) |
| 데이터베이스 | PostgreSQL (운영) / SQLite (개발), Alembic |
| AI / LLM | OpenAI GPT-4o-mini, OpenAI TTS |
| 음성 인식 | Azure Cognitive Services Speech / Web Speech API |
| 이메일 | Brevo (트랜잭션 메일 — 이메일 인증, 비밀번호 재설정) |
| 캐시 | Redis 7 (선택) |
| 스케줄러 | APScheduler 3.10.4 |
| 웹 푸시 | pywebpush 2.3.0 |
| 프론트엔드 | Vanilla JS (ES6+), Tailwind CSS, tsParticles |
| DevOps | Docker, Docker Compose, Nginx, Let's Encrypt |
| 인프라 | Terraform, AWS (EC2, RDS), Cloudflare (도메인 haru-commit.com) |
