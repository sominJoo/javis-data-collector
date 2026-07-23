import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_API_KEY_PREFIX = "sk-graphio-"
_API_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
_PBKDF2_ROUNDS = 200_000

settings = get_settings()

_bearer_scheme = HTTPBearer(auto_error=False)


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    """토큰에서 복원한 요청 주체."""

    role: Role
    subject: str
    api_key_id: str | None = None  # role=user 일 때 사용자 DB 라우팅 키
    admin_id: str | None = None  # role=admin 일 때


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {"sub": subject}
    # jwt_expire_minutes<=0 이면 만료 없는 토큰(exp 미포함). 그 외에는 분 단위 만료.
    if settings.jwt_expire_minutes > 0:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# ---------- API Key 발급/해시 ----------
def generate_api_key() -> str:
    body = "".join(secrets.choice(_API_KEY_ALPHABET) for _ in range(32))
    return f"{_API_KEY_PREFIX}{body}"


def mask_api_key(plain: str) -> str:
    return f"{_API_KEY_PREFIX}{'•' * 10}{plain[-4:]}"


def hash_api_key(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


# ---------- 관리자 비밀번호 해시 (PBKDF2-HMAC-SHA256) ----------
def hash_password(plain: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(plain: str, stored: str) -> bool:
    try:
        scheme, b64salt, b64dk = stored.split("$")
        if scheme != "pbkdf2":
            return False
        salt = base64.b64decode(b64salt)
        expected = base64.b64decode(b64dk)
        candidate = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt, _PBKDF2_ROUNDS)
        return hmac.compare_digest(candidate, expected)
    except (ValueError, TypeError):
        return False


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
        ) from exc


async def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization 헤더가 필요합니다.",
        )
    return decode_access_token(credentials.credentials)


async def get_current_principal(
    payload: dict[str, Any] = Depends(get_current_token_payload),
) -> Principal:
    try:
        role = Role(payload.get("role", ""))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        ) from exc
    return Principal(
        role=role,
        subject=str(payload.get("sub", "")),
        api_key_id=payload.get("api_key_id"),
        admin_id=payload.get("admin_id"),
    )


async def require_user(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """API Key 로그인 사용자 전용(사용자 DB 라우팅에 api_key_id 필요)."""
    if principal.role is not Role.USER or not principal.api_key_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="사용자 권한이 필요합니다.",
        )
    return principal


async def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """관리자 전용."""
    if principal.role is not Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다.",
        )
    return principal
