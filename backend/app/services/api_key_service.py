import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import crypto
from app.core.security import generate_api_key, hash_api_key, mask_api_key
from app.models.collector import (
    API_KEY_ACTIVE,
    API_KEY_DISABLED,
    ApiKeyDbConnection,
    ApiKeyEmbeddingConfig,
    ApiKeyLlmConfig,
    CollectorApiKey,
)
from app.schemas.api_key import (
    ApiKeyIn,
    ApiKeyOut,
    DbConnectionSchema,
    EmbeddingConfigSchema,
    LlmConfigSchema,
)
from app.services import db_credential_stage
from app.services.errors import NotFoundError

__all__ = ["NotFoundError", "list_api_keys", "create_api_key", "update_api_key", "toggle_api_key"]


def _identity(host: str, port: int, database: str, username: str) -> str:
    return f"{username}@{host}:{port}/{database}"


def _enc_secret(raw: str | None) -> str | None:
    """평문 시크릿을 암호화. 빈값이면 None(미저장)."""
    raw = (raw or "").strip()
    return crypto.encrypt(raw) if raw else None


def _to_out(key: CollectorApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=str(key.id),
        name=key.name,
        key_masked=key.api_key_masked,
        active=key.status == API_KEY_ACTIVE,
        expire_at=key.expired_at,
        last_used_at=key.last_used_at,
        llm=LlmConfigSchema(
            provider=key.llm.provider,
            endpoint=key.llm.endpoint,
            model=key.llm.model,
            kind=key.llm.kind,
            has_secret=bool(key.llm.secret_encrypted),  # secret 값 자체는 응답에 담지 않음
        ),
        embedding=EmbeddingConfigSchema(
            provider=key.embedding.provider,
            endpoint=key.embedding.endpoint,
            model=key.embedding.model,
            kind=key.embedding.kind,
            has_secret=bool(key.embedding.secret_encrypted),
        ),
        db_connections=[
            DbConnectionSchema(
                id=str(c.id),
                name=c.name,
                host=c.host,
                port=c.port,
                database=c.database,
                username=c.username,
                is_default=c.is_default,
            )
            for c in key.db_connections
        ],
    )


def _load_stmt():
    return select(CollectorApiKey).options(
        selectinload(CollectorApiKey.llm),
        selectinload(CollectorApiKey.embedding),
        selectinload(CollectorApiKey.db_connections),
    )


async def _load_one(db: AsyncSession, key_id: uuid.UUID) -> CollectorApiKey:
    key = await db.scalar(_load_stmt().where(CollectorApiKey.id == key_id))
    if key is None:
        raise NotFoundError("API Key를 찾을 수 없습니다.")
    return key


def _parse_id(key_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(key_id)
    except ValueError as exc:
        raise NotFoundError("API Key를 찾을 수 없습니다.") from exc


async def list_api_keys(db: AsyncSession) -> list[ApiKeyOut]:
    keys = (await db.scalars(_load_stmt().order_by(CollectorApiKey.created_at))).all()
    return [_to_out(k) for k in keys]


def _build_connection(
    c: DbConnectionSchema, existing_pw: dict[str, str | None] | None = None
) -> ApiKeyDbConnection:
    enc = db_credential_stage.take(c.host, c.port, c.database, c.username)
    if enc is None and existing_pw is not None:
        enc = existing_pw.get(_identity(c.host, c.port, c.database, c.username))
    return ApiKeyDbConnection(
        name=c.name,
        host=c.host,
        port=c.port,
        database=c.database,
        username=c.username,
        password_encrypted=enc,
        is_default=c.is_default,
    )


async def create_api_key(db: AsyncSession, payload: ApiKeyIn) -> ApiKeyOut:
    plain = generate_api_key()
    key = CollectorApiKey(
        name=payload.name,
        api_key_hash=hash_api_key(plain),
        api_key_masked=mask_api_key(plain),
        status=API_KEY_ACTIVE if payload.active else API_KEY_DISABLED,
        expired_at=payload.expire_at,
    )
    key.llm = ApiKeyLlmConfig(
        provider=payload.llm.provider,
        endpoint=payload.llm.endpoint,
        model=payload.llm.model,
        kind=payload.llm.kind,
        secret_encrypted=_enc_secret(payload.llm.secret),
    )
    key.embedding = ApiKeyEmbeddingConfig(
        provider=payload.embedding.provider,
        endpoint=payload.embedding.endpoint,
        model=payload.embedding.model,
        kind=payload.embedding.kind,
        secret_encrypted=_enc_secret(payload.embedding.secret),
    )
    for c in payload.db_connections:
        key.db_connections.append(_build_connection(c))

    db.add(key)
    await db.commit()

    out = _to_out(await _load_one(db, key.id))
    out.key_plain = plain  # 평문은 발급 응답에만 1회 노출
    return out


async def update_api_key(db: AsyncSession, key_id: str, payload: ApiKeyIn) -> ApiKeyOut:
    key = await _load_one(db, _parse_id(key_id))
    key.name = payload.name
    key.status = API_KEY_ACTIVE if payload.active else API_KEY_DISABLED
    key.expired_at = payload.expire_at
    key.llm.provider = payload.llm.provider
    key.llm.endpoint = payload.llm.endpoint
    key.llm.model = payload.llm.model
    key.llm.kind = payload.llm.kind
    # 시크릿은 입력이 있을 때만 교체(빈값이면 기존값 유지 — DB 비밀번호와 동일 패턴)
    if (payload.llm.secret or "").strip():
        key.llm.secret_encrypted = _enc_secret(payload.llm.secret)
    key.embedding.provider = payload.embedding.provider
    key.embedding.endpoint = payload.embedding.endpoint
    key.embedding.model = payload.embedding.model
    key.embedding.kind = payload.embedding.kind
    if (payload.embedding.secret or "").strip():
        key.embedding.secret_encrypted = _enc_secret(payload.embedding.secret)

    existing_pw = {
        _identity(c.host, c.port, c.database, c.username): c.password_encrypted
        for c in key.db_connections
    }
    key.db_connections.clear()
    await db.flush()
    for c in payload.db_connections:
        key.db_connections.append(_build_connection(c, existing_pw))

    await db.commit()
    return _to_out(await _load_one(db, key.id))


async def toggle_api_key(db: AsyncSession, key_id: str) -> None:
    key = await db.get(CollectorApiKey, _parse_id(key_id))
    if key is None:
        raise NotFoundError("API Key를 찾을 수 없습니다.")
    key.status = API_KEY_DISABLED if key.status == API_KEY_ACTIVE else API_KEY_ACTIVE
    await db.commit()
