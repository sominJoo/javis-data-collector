# jarivs-data-collector

Graphio Core Agent 데이터 수집기

## 아키텍처 개요

파일 업로드 → 원문 분석(LangChain/LangGraph, LLM) → Summary/Chunk/Embedding/Report Skill 생성 → 사용자 DB 저장.
Nuxt Frontend + FastAPI Backend(BackgroundTasks 기반 비동기 처리, Queue/Redis/Celery 미사용) 2개 프로세스로 동작하며,
PostgreSQL 16(+pgvector)에 `collector_service`(운영), `jarvis`/`data_collector`(사용자) 3개 스키마를 사용한다.

## 실행 방법

실행 방식은 두 가지다.

| 구분 | 용도 | 방법 |
| --- | --- | --- |
| **개발 실행** | 로컬 개발·디버깅 (코드 변경 시 자동 리로드) | 백엔드 `uvicorn --reload`(또는 IDE 디버거) + 프론트엔드 `npm run dev` |
| **실제 실행** | 배포·상시 구동 | `./install.sh` 설치 후 `./javis` CLI로 백그라운드 서버 제어 |

공통 사전 요구사항: PostgreSQL 16 (+pgvector 확장), Python 3.11, Node.js `^20.19.0 || >=22.12.0`.

---

## 1. 개발 실행

백엔드와 프론트엔드를 각각 실행한다.

### Backend (`backend/`)

FastAPI + SQLAlchemy 2.x Async + Alembic + LangChain/LangGraph, **Python 3.11**.

```bash
cd backend

# 1) Python 환경 (conda 또는 venv 중 택1)
conda env create -f environment.yml && conda activate jarivs-data-collector
#   또는
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2) 환경변수
cp .env.example .env   # POSTGRES_*, JWT_SECRET, ENCRYPTION_KEY, INITIAL_ADMIN_* 등 값 채우기

# 3) 서버 실행 (--reload: 코드 변경 시 자동 재기동)
uvicorn main:app --reload
```

- 기동 시 운영 스키마(`collector_service`)는 `AUTO_MIGRATE=true`(기본값)면 자동 마이그레이션된다 — 수동 `alembic upgrade head` 불필요.
- 초기 관리자 계정은 `INITIAL_ADMIN_ID` / `INITIAL_ADMIN_PASSWORD` 값으로 마이그레이션 시 생성된다.
- IDE 디버거로 실행할 경우 작업 디렉터리를 `backend/`로 두고 진입점을 `uvicorn main:app`(또는 `main.py`)으로 설정한다.
- API 문서: `http://localhost:8000/docs`
- 헬스체크: `GET http://localhost:8000/api/v1/health`
- 테스트: `pytest`

### Frontend (`frontend/`)

Nuxt 3 + Vue 3 + TypeScript + Pinia + SCSS. **Node.js `^20.19.0 || >=22.12.0` 필요**(`frontend/.nvmrc` = `22`).

```bash
cd frontend
nvm use            # .nvmrc(22) 기준. 설치돼 있지 않으면 nvm install
npm install
cp .env.example .env   # NUXT_PUBLIC_API_BASE_URL 확인 (기본 http://localhost:8000/api/v1)
npm run dev
```

- `http://localhost:3000` 접속하여 확인

---

## 2. 실제 실행 (설치 후 `javis`)

빌드 산출물을 백그라운드 서버로 구동하는 배포용 방식이다. 저장소 루트에서 실행한다.

### 1) 설치

```bash
./install.sh                 # conda 감지 시 방식을 물어보고, 없으면 venv 사용
# 또는 방식을 명시:
./install.sh --venv
./install.sh --conda [환경이름]
```

`install.sh`가 수행하는 작업:

1. python / node 등 사전 도구 확인 (Node `>=20.19` 또는 `>=22.12`)
2. 백엔드 Python 환경 구성 + 의존성 설치 (conda 또는 `.venv`)
3. 프론트엔드 의존성 설치 + 빌드 (`nuxt build` → `.output`)
4. `backend/.env` · `frontend/.env` 생성 (JWT/ENCRYPTION 시크릿 자동 생성)
5. 실행 정보 기록 (`.run/env.conf`) — `javis`가 서버 실행에 사용

> 설치 후 `backend/.env`의 DB 접속정보(`POSTGRES_*`)와 초기 관리자(`INITIAL_ADMIN_*`) 값을 확인·보완한다.

### 2) 실행 / 제어

```bash
./javis start     # 백엔드(uvicorn) + 프론트엔드(Nuxt node 서버) 백그라운드 기동
./javis status    # 실행 상태 확인
./javis stop      # 중지
./javis restart   # 재시작
```

- 프론트엔드: `http://localhost:3000`
- 백엔드 API: `http://localhost:8000/api/v1`
- API 문서: `http://localhost:8000/docs`
- 로그: `tail -f .run/backend.log` / `tail -f .run/frontend.log`
