from datetime import datetime

from app.schemas.base import CamelModel


class LlmConfigSchema(CamelModel):
    provider: str = "openai"
    endpoint: str
    model: str


class EmbeddingConfigSchema(CamelModel):
    provider: str = "openai"
    endpoint: str
    model: str


class DbConnectionSchema(CamelModel):
    id: str = ""
    name: str
    host: str
    port: int = 5432
    database: str
    username: str
    is_default: bool = False


class ApiKeyIn(CamelModel):
    """생성/수정 요청. FE는 전체 ApiKey 객체를 보내며 keyMasked/lastUsedAt 등은 무시한다."""

    id: str = ""
    name: str
    expire_at: datetime | None = None
    active: bool = True
    llm: LlmConfigSchema
    embedding: EmbeddingConfigSchema
    db_connections: list[DbConnectionSchema] = []


class ApiKeyOut(CamelModel):
    id: str
    name: str
    key_masked: str
    key_plain: str | None = None  # 발급(POST) 시에만 채워짐
    active: bool
    expire_at: datetime | None = None
    last_used_at: datetime | None = None
    llm: LlmConfigSchema
    embedding: EmbeddingConfigSchema
    db_connections: list[DbConnectionSchema] = []
