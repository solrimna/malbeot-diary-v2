## 시작하기

1. 저장소 clone
git clone https://github.com/solrimna/malbeot-diary.git

2. 환경변수 세팅
cp .env.example .env

3. 의존성 설치
pip install uv
uv pip install --system -r requirements.txt

4. 로컬 DB/Redis 실행
docker compose up db redis -d

5. 서버 실행
uvicorn app.main:app --reload
