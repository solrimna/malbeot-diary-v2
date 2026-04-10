# pytest 흐름 이해하기

이 프로젝트의 테스트 구조를 기준으로 설명합니다.

---

## 1. conftest.py는 어떻게 실행되나요?

`conftest.py`는 직접 호출하거나 import하지 않아도 됩니다.  
`pytest`를 실행하면 pytest가 **자동으로** `conftest.py`를 찾아서 읽습니다.

```bash
pytest tests/
# pytest가 tests/ 폴더를 탐색하면서 conftest.py를 자동 로딩
```

---

## 2. 전체 실행 흐름

```
pytest tests/ 실행
    │
    ├── 1. conftest.py 자동 로딩
    │       - import app.models (테이블 등록)
    │       - _engine, _SessionLocal 생성
    │       - fixture 함수들 등록 (아직 실행 안 함)
    │
    ├── 2. setup_db 실행 (scope="session", autouse=True)
    │       - 테스트 전체에서 딱 1번 실행
    │       - 인메모리 SQLite에 테이블 CREATE
    │
    ├── 3. test_register 실행
    │       ├── clean_tables (autouse) → 모든 행 DELETE
    │       ├── db fixture      → DB 세션 생성
    │       ├── client fixture  → HTTP 테스트 클라이언트 생성 (GPT 모킹 적용)
    │       └── 테스트 본문 실행
    │
    ├── 4. test_register_duplicate 실행
    │       ├── clean_tables → 다시 모든 행 DELETE  ← 테스트 격리 핵심
    │       ├── db, client fixture 다시 생성
    │       └── 테스트 본문 실행
    │
    └── 5. 나머지 테스트 동일하게 반복 → 결과 출력
```

---

## 3. fixture란?

테스트에 필요한 것들을 **미리 준비해주는 함수**입니다.  
테스트 함수의 **파라미터 이름**으로 자동 주입됩니다.

```python
# conftest.py
@pytest.fixture
async def client(db):       # "client"라는 이름으로 등록
    ...
    yield ac                # yield 앞 = 준비(setup), yield 뒤 = 정리(teardown)
```

```python
# test_auth.py
async def test_register(client):   # ← 파라미터 이름이 "client" → 자동 주입
    res = await client.post(...)
```

pytest가 파라미터 이름을 보고 같은 이름의 fixture를 찾아서 실행 후 주입해줍니다.

### fixture 의존성 체인

fixture는 다른 fixture를 파라미터로 받을 수 있습니다.

```
test_create_diary(client, auth_headers)
    │                  │
    │                  └── auth_headers(client)
    │                              │
    └──────────── client(db) ──────┘
                        │
                        db()
```

`db` → `client` → `auth_headers` 순서로 준비되고,  
테스트가 끝나면 역순으로 정리(teardown)됩니다.

---

## 4. scope: 얼마나 자주 재생성할지

| scope | 실행 횟수 | 이 프로젝트에서 사용 |
|-------|----------|---------------------|
| `"session"` | 전체 테스트에서 **1번** | `setup_db` (테이블 생성) |
| `"module"` | 테스트 파일마다 1번 | - |
| `"function"` (기본값) | **테스트마다** | `db`, `client`, `clean_tables` |

```python
@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # 전체 테스트 시작 전 딱 1번 → 테이블 생성
    ...

@pytest.fixture(autouse=True)
async def clean_tables():
    # 매 테스트마다 → 데이터 초기화 (테스트 격리)
    ...
```

---

## 5. autouse: 파라미터 없이 자동 실행

`autouse=True`를 붙이면 테스트 함수에 파라미터로 명시하지 않아도 자동으로 실행됩니다.

```python
# autouse=True → 모든 테스트에서 자동 실행
@pytest.fixture(autouse=True)
async def clean_tables():
    ...

# 테스트 함수에 clean_tables를 명시하지 않아도 자동 적용됨
async def test_register(client):
    ...
```

---

## 6. yield: 준비와 정리 분리

```python
@pytest.fixture
async def client(db):
    # ── setup (테스트 실행 전) ──────────────
    app.dependency_overrides[get_db] = _override
    async with AsyncClient(...) as ac:

        yield ac        # ← 테스트 본문 실행

    # ── teardown (테스트 실행 후) ───────────
    app.dependency_overrides.clear()
```

`yield` 앞은 준비, `yield` 뒤는 정리입니다.  
테스트가 성공하든 실패하든 `yield` 이후 코드는 항상 실행됩니다.

---

## 7. 이 프로젝트의 fixture 역할 요약

| fixture | scope | autouse | 역할 |
|---------|-------|---------|------|
| `setup_db` | session | ✅ | 인메모리 SQLite에 테이블 생성 (1회) |
| `clean_tables` | function | ✅ | 매 테스트 전 전체 데이터 삭제 |
| `db` | function | ❌ | 테스트용 DB 세션 제공 |
| `client` | function | ❌ | HTTP 클라이언트 + GPT 모킹 + DB 주입 |
| `auth_headers` | function | ❌ | 회원가입/로그인 후 JWT 헤더 반환 |

---

## 8. 테스트 격리가 왜 중요한가?

`clean_tables`가 없으면 테스트끼리 데이터가 섞입니다.

```
# clean_tables 없을 때 문제 예시
test_register        → users 테이블에 "testuser" 추가
test_register_duplicate → "testuser" 이미 있으니 409... 근데 이건 clean 안 해서 그런 건지 코드가 맞아서 그런 건지 알 수 없음

# clean_tables 있을 때
test_register        → users 비어있음 → "testuser" 추가 → 201 ✅
clean_tables 실행    → users 비워짐
test_register_duplicate → "testuser" 추가(201) → 다시 "testuser" 추가 → 409 ✅
```

각 테스트는 독립적으로 실행되어야 순서나 실행 횟수에 상관없이 항상 같은 결과가 나옵니다.

---

---

## 9. SQLite vs PostgreSQL — 어디서 어떻게 테스트하나?

### 왜 두 가지 DB로 테스트하나?

| | SQLite | PostgreSQL |
|---|---|---|
| 속도 | 빠름 | 상대적으로 느림 |
| 설치 | 불필요 (인메모리) | 서버 필요 |
| 용도 | 로컬 개발, PR 빠른 피드백 | 배포 전 실제 운영 환경 검증 |

같은 테스트 코드가 두 DB에서 모두 동작하는 이유는 SQLAlchemy가 DB 종류를 추상화해주기 때문입니다. 테스트 코드는 바꾸지 않고 연결 URL만 바꾸면 됩니다.

### conftest.py의 환경변수 분기

```python
# TEST_DATABASE_URL 환경변수가 없으면 SQLite, 있으면 해당 DB 사용
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

if "sqlite" in TEST_DB_URL:
    _engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # SQLite 전용: 단일 커넥션 공유
    )
else:
    _engine = create_async_engine(TEST_DB_URL)  # PostgreSQL 등
```

`StaticPool`은 SQLite 인메모리 특성상 커넥션마다 DB가 새로 생기는 문제를 막기 위해 사용합니다. PostgreSQL은 이 문제가 없으므로 그냥 씁니다.

### GitHub Actions에서의 전체 흐름

`main` 브랜치에 push하면 GitHub 서버(ubuntu-latest)에서 자동으로 실행됩니다.

```
개발자 로컬              GitHub Actions               EC2 서버
──────────────────────────────────────────────────────────────
코드 작성
    │
git push origin main
    │
    └──────────────▶  [test job]
                      pytest 실행 (SQLite, 환경변수 없음)
                           │ 통과
                      [test-postgres job]
                      ┌─────────────────────────────┐
                      │ GitHub 서버 안에서           │
                      │ PostgreSQL 컨테이너 자동 시작│
                      │   image: postgres:16         │
                      │   user/pw/db: test           │
                      │   port: 5432                 │
                      └─────────────────────────────┘
                      TEST_DATABASE_URL=postgresql+asyncpg://...
                      pytest 실행 (PostgreSQL)
                           │ 통과
                      [deploy job]
                      Docker 빌드 & 푸시
                           │
                           └──────────────▶ EC2에 배포
```

deploy job은 `needs: [test, test-postgres]`로 설정되어 있어 **두 테스트 job이 모두 통과해야만 배포가 진행됩니다.**

### PR일 때와 main push일 때의 차이

```
PR (feature/* → main)
    └── test (SQLite) 만 실행    ← 빠른 피드백

main 브랜치 push
    ├── test (SQLite)
    ├── test-postgres (PostgreSQL)  ← 배포 전 실제 환경 검증
    └── deploy (위 둘 통과 시)
```

---

## 참고

- [pytest 공식 문서](https://docs.pytest.org)
- [pytest-asyncio 문서](https://pytest-asyncio.readthedocs.io)
- [GitHub Actions 서비스 컨테이너](https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers)
