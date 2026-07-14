from datetime import datetime

from app.schemas.base import CamelModel


class LlmConfigSchema(CamelModel):
    provider: str = "openai"
    endpoint: str
    model: str
    kind: str = "CLOUD"  # LOCAL(자격 불필요) | CLOUD(시크릿 필요)
    secret: str | None = None  # 입력 전용. 빈값이면 수정 시 기존값 유지. 출력에는 미포함
    has_secret: bool = False  # 출력 전용. 저장된 시크릿 존재 여부(UI 표시용)


class EmbeddingConfigSchema(CamelModel):
    provider: str = "openai"
    endpoint: str
    model: str
    kind: str = "CLOUD"  # LOCAL(자격 불필요) | CLOUD(시크릿 필요)
    secret: str | None = None  # 입력 전용. 빈값이면 수정 시 기존값 유지. 출력에는 미포함
    has_secret: bool = False  # 출력 전용. 저장된 시크릿 존재 여부(UI 표시용)


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
