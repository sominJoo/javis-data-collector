#!/usr/bin/env bash
#
# 데이터 수집기 · 네이티브 설치 스크립트
#   사용법:  ./install.sh [--conda [환경이름] | --venv]
#     --conda [이름] : conda 환경으로 backend 구성 (이름 생략 시 물어봄)
#     --venv         : .venv (Python venv)로 backend 구성
#     (옵션 생략 시 conda가 있으면 물어보고, 없으면 venv 사용)
#
#   하는 일:
#     1) python / node 등 사전 도구 확인
#     2) backend Python 환경 구성 + 의존성 설치 (conda 또는 venv)
#     3) frontend 의존성 설치 + 빌드 (nuxt build → .output)
#     4) backend/.env · frontend/.env 생성
#        (JWT_SECRET 은 항상 새로 생성. ENCRYPTION_KEY 는 기존 DB 재사용 시
#         그때 쓰던 키를 입력받아 유지, 신규면 새로 생성)
#     5) 실행 정보 기록 (.run/env.conf) — javis 가 서버 실행에 사용
#     6) javis 실행 권한 부여
#
#   설치 후:  ./javis start   (stop | status | restart)
#
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

log() { printf '  %s\n' "$*"; }
ok()  { printf '\033[32m✓\033[0m %s\n' "$*"; }
err() { printf '\033[31m✗\033[0m %s\n' "$*" >&2; }

# ── 1) 환경 방식 결정 ────────────────────────────────────────
MODE=""
ENV_NAME_ARG=""
case "${1:-}" in
  --conda) MODE=conda; ENV_NAME_ARG="${2:-}" ;;
  --venv)  MODE=venv ;;
  "")      ;;
  *) err "알 수 없는 옵션: $1  (사용: --conda [환경이름] | --venv)"; exit 1 ;;
esac

if [ -z "$MODE" ]; then
  if command -v conda >/dev/null 2>&1; then
    read -rp "Python 환경 방식 [conda/venv] (conda 감지됨, 기본 conda): " MODE
    MODE="${MODE:-conda}"
  else
    MODE=venv
    log "conda 미감지 → venv 로 진행"
  fi
fi
[ "$MODE" = conda ] || [ "$MODE" = venv ] || { err "conda 또는 venv 만 가능 (입력: $MODE)"; exit 1; }

# ── 2) 사전 도구 확인 ────────────────────────────────────────
if [ "$MODE" = conda ]; then
  command -v conda >/dev/null 2>&1 || { err "conda 가 필요합니다."; exit 1; }
else
  command -v python3 >/dev/null 2>&1 || { err "python3 가 필요합니다."; exit 1; }
fi
command -v node >/dev/null 2>&1 || { err "node(>=20.19 또는 >=22.12)가 필요합니다."; exit 1; }
command -v npm  >/dev/null 2>&1 || { err "npm 이 필요합니다."; exit 1; }
ok "사전 도구 확인 (mode=${MODE}, node $(node -v))"

# ── 3) backend Python 환경 구성 ─────────────────────────────
if [ "$MODE" = conda ]; then
  # 사용할 conda 환경 이름: 인자 > 입력 > 기본값(현재 활성 env, base면 environment.yml name)
  if [ -n "$ENV_NAME_ARG" ]; then
    CONDA_ENV_NAME="$ENV_NAME_ARG"
  else
    _def="${CONDA_DEFAULT_ENV:-}"
    { [ -z "$_def" ] || [ "$_def" = "base" ]; } && _def="$(awk '/^name:/{print $2}' backend/environment.yml)"
    read -rp "사용할 conda 환경 이름 (기본: ${_def}): " CONDA_ENV_NAME
    CONDA_ENV_NAME="${CONDA_ENV_NAME:-$_def}"
  fi
  log "conda 환경 구성 (${CONDA_ENV_NAME})..."
  # env create/update -f yml (특히 --prune)은 solver를 무겁게 돌려 일부 conda에서
  # Segmentation fault 를 유발한다. python 만 conda로 만들고 의존성은 pip로 설치해
  # solver 부담을 최소화한다. (environment.yml 도 실질은 python=3.11 + pip -r requirements.txt)
  if conda env list | awk '{print $1}' | grep -qx "$CONDA_ENV_NAME"; then
    log "기존 conda 환경 재사용"
  else
    conda create -y -n "$CONDA_ENV_NAME" python=3.11
  fi
  conda run --no-capture-output -n "$CONDA_ENV_NAME" python -m pip install --upgrade pip
  conda run --no-capture-output -n "$CONDA_ENV_NAME" python -m pip install -r backend/requirements.txt
  PYTHON_BIN="$(conda run -n "$CONDA_ENV_NAME" python -c 'import sys,os;print(os.path.join(sys.prefix,"bin","python"))')"
  UVICORN_BIN="$(dirname "$PYTHON_BIN")/uvicorn"
else
  log "venv 구성 (.venv)..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip -q
  ./.venv/bin/pip install -r backend/requirements.txt
  PYTHON_BIN="$ROOT/.venv/bin/python"
  UVICORN_BIN="$ROOT/.venv/bin/uvicorn"
fi
ok "backend 의존성 설치 완료"

# ── 4) frontend 의존성 설치 + 빌드 ──────────────────────────
log "frontend 의존성 설치 및 빌드 (nuxt build)..."
( cd frontend && npm ci && npm run build )
ok "frontend 빌드 완료 (.output)"

# ── 5) .env 생성 (+ 시크릿 자동 생성) ───────────────────────
# 입력받은 문자열이 유효한 Fernet 키(urlsafe base64 32바이트)인지 검증.
_is_valid_fernet() {
  FERNET_CANDIDATE="$1" "$PYTHON_BIN" - <<'PY' 2>/dev/null
import os
from cryptography.fernet import Fernet
Fernet(os.environ["FERNET_CANDIDATE"].encode())
PY
}

# ENCRYPTION_KEY 결정.
#   기존 데이터(암호화된 DB 비밀번호 등)가 있는 DB를 계속 쓰면, 그때 쓰던 키를
#   그대로 넣어야 기존 암호값을 복호화할 수 있다. 키가 바뀌면 복호화 불가(InvalidToken).
#   결과 키는 화면에 출력하지 않고 전역 RESOLVED_FERNET 에 담는다.
resolve_encryption_key() {
  local reuse fernet
  read -rp "이전에 사용하던 DB(암호화된 데이터 포함)를 계속 사용하나요? [y/N]: " reuse
  if [ "$reuse" = y ] || [ "$reuse" = Y ]; then
    while :; do
      # 시크릿이므로 입력값을 화면에 표시하지 않는다(-s).
      read -rsp "그때 사용하던 ENCRYPTION_KEY 를 입력하세요: " fernet; printf '\n'
      if [ -n "$fernet" ] && _is_valid_fernet "$fernet"; then
        ok "기존 ENCRYPTION_KEY 사용 (기존 데이터 복호화 유지)"
        break
      fi
      err "유효한 Fernet 키가 아닙니다. 다시 입력하세요. (Ctrl-C 로 중단)"
    done
  else
    fernet="$("$PYTHON_BIN" -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
    ok "새 ENCRYPTION_KEY 생성"
  fi
  RESOLVED_FERNET="$fernet"
}

create_backend_env() {
  if [ -f backend/.env ]; then
    read -rp "backend/.env 가 이미 있습니다. 덮어쓸까요? [y/N]: " ow
    { [ "$ow" = y ] || [ "$ow" = Y ]; } || { log "backend/.env 유지"; return; }
  fi
  cp backend/.env.example backend/.env
  local jwt
  jwt="$(openssl rand -hex 32)"          # JWT_SECRET 은 데이터와 무관 → 항상 새로 생성(재로그인만 필요)
  resolve_encryption_key                 # → RESOLVED_FERNET
  sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=${jwt}|"                    backend/.env
  sed -i.bak "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${RESOLVED_FERNET}|" backend/.env
  rm -f backend/.env.bak
  ok "backend/.env 생성 완료"
}

create_frontend_env() {
  [ -f frontend/.env.example ] || { log "frontend/.env.example 없음 — 건너뜀"; return; }
  if [ -f frontend/.env ]; then log "frontend/.env 유지"; return; fi
  cp frontend/.env.example frontend/.env
  ok "frontend/.env 생성"
}

create_backend_env
create_frontend_env

# ── 6) 실행 정보 기록 (.run/env.conf) ───────────────────────
mkdir -p .run
cat > .run/env.conf <<EOF
# javis 가 서버 실행에 사용하는 값 (install.sh 가 생성 — 수동 편집 비권장)
ENV_MODE=${MODE}
PYTHON_BIN=${PYTHON_BIN}
UVICORN_BIN=${UVICORN_BIN}
NODE_BIN=$(command -v node)
EOF
ok "실행 환경 기록 (.run/env.conf)"

# ── 7) javis 실행 권한 ──────────────────────────────────────
chmod +x javis 2>/dev/null || true

printf '\n\033[32m설치 완료\033[0m\n'
log "서버 시작:  ./javis start"
log "상태 확인:  ./javis status"
log "중지:       ./javis stop"
log ""
log "• 백엔드 API : http://localhost:8000/api/v1"
log "• API 문서   : http://localhost:8000/docs"
log "• 프론트엔드 : http://localhost:3000"
