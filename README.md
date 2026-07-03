# jarivs-data-collector

Graphio Core Agent 데이터 수집기

## 아키텍처 개요

파일 업로드 → 원문 분석(LangChain/LangGraph, LLM) → Summary/Chunk/Embedding/Report Skill 생성 → 사용자 DB 저장.
Nuxt Frontend + FastAPI Backend(BackgroundTasks 기반 비동기 처리, Queue/Redis/Celery 미사용) 2-컨테이너 구조이며,
PostgreSQL 16(+pgvector)에 `collector_service`(운영), `jarvis`/`data_collector`(사용자) 3개 스키마를 사용한다.
자세한 내용은 [docs/](docs) 하위 설계/정책 문서를 참고한다.

## Backend (`backend/`)

FastAPI + SQLAlchemy 2.x Async + Alembic + LangChain/LangGraph, Python 3.11 (Conda).

```bash
cd backend
conda env create -f environment.yml
conda activate jarivs-data-collector
cp .env.example .env   # 값 채우기

# 로컬 PostgreSQL(pgvector)이 필요하다면 docker/docker-compose.yml의 db 서비스만 기동 가능:
# docker compose -f ../docker/docker-compose.yml up -d db

alembic upgrade head
uvicorn main:app --reload
```

- API 문서: `http://localhost:8000/docs`
- 헬스체크: `GET http://localhost:8000/api/v1/health`
- 테스트: `pytest`

## Frontend (`frontend/`)

Nuxt 3 + Vue 3 + TypeScript + Pinia + SCSS. Node.js `^20.19.0 || >=22.12.0` 필요 (Nuxt/Vite 최신 버전 요구사항).
nvm 사용 시 `frontend/.nvmrc`에 맞춰 버전을 전환한다.

```bash
cd frontend
nvm install   # .nvmrc(22) 기준 설치, 이미 있다면 nvm use
nvm use
npm install
cp .env.example .env   # 값 확인
npm run dev
```

- `http://localhost:3000` 접속하여 확인

## Docker로 한 번에 실행

```bash
docker compose -f docker/docker-compose.yml up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL(pgvector): `localhost:5432`
