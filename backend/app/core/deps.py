"""요청 스코프 의존성.

`get_user_db`: 로그인한 API Key의 기본 DB 연결을 해석해 사용자 DB용 AsyncSession을 주입한다.
`get_user_context`: 사용자 DB 세션 + 해당 API Key(LLM/Embedding 설정 포함)를 함께 제공한다.
"""
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import crypto
from app.core.database import get_db
from app.core.security import Principal, require_user
from app.core.user_db import UserDbParams, user_session
from app.models.collector import ApiKeyDbConnection, CollectorApiKey


async def _load_api_key(collector: AsyncSession, api_key_id: str) -> CollectorApiKey:
    try:
        kid = uuid.UUID(api_key_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다.") from exc
    key = await collector.scalar(
        select(CollectorApiKey)
        .options(
            selectinload(CollectorApiKey.db_connections),
            selectinload(CollectorApiKey.llm),
            selectinload(CollectorApiKey.embedding),
        )
        .where(CollectorApiKey.id == kid)
    )
    if key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 API Key입니다.")
    return key


def _default_connection(key: CollectorApiKey) -> ApiKeyDbConnection:
    conns = key.db_connections
    if not conns:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "이 API Key에 등록된 DB 연결이 없습니다. 관리자에게 문의하세요.",
        )
    return next((c for c in conns if c.is_default), conns[0])


def _params(conn: ApiKeyDbConnection) -> UserDbParams:
    password = crypto.decrypt(conn.password_encrypted) if conn.password_encrypted else ""
    return UserDbParams(
        host=conn.host,
        port=conn.port,
        database=conn.database,
        username=conn.username,
        password=password,
    )


def user_db_params(api_key: CollectorApiKey) -> UserDbParams:
    """API Key의 기본 DB 연결로부터 사용자 DB 접속 파라미터를 만든다.

    백그라운드 태스크가 요청 스코프 세션과 무관하게 사용자 DB에 접속할 때 쓴다.
    (요청 처리 중에 미리 호출해 plain 값으로 캡처할 것 — 평문 비밀번호를 담으므로 로그 금지)
    """
    return _params(_default_connection(api_key))


async def get_user_db(
    principal: Principal = Depends(require_user),
    collector: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    key = await _load_api_key(collector, principal.api_key_id or "")
    params = _params(_default_connection(key))
    async with user_session(params) as session:
        yield session


@dataclass
class UserContext:
    session: AsyncSession  # 사용자 DB (jarvis / data_collector)
    api_key: CollectorApiKey
    collector: AsyncSession  # 수집기 운영 DB (collector_service) — staging 등


async def get_user_context(
    principal: Principal = Depends(require_user),
    collector: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UserContext, None]:
    key = await _load_api_key(collector, principal.api_key_id or "")
    params = _params(_default_connection(key))
    async with user_session(params) as session:
        yield UserContext(session=session, api_key=key, collector=collector)
