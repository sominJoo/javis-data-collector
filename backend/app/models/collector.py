"""collector_service 스키마 모델 (수집기 자체 DB).

API Key / LLM·Embedding 설정 / DB 연결 / 관리자 계정 / 이력만 보관한다.
원본 데이터·청크·임베딩은 여기 저장하지 않고 사용자 DB(user_data.py)에 둔다.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Schema
from app.models.mixins import TimestampMixin, UuidPkMixin

_SCHEMA = {"schema": Schema.COLLECTOR_SERVICE}


def _fk(target: str) -> str:
    return f"{Schema.COLLECTOR_SERVICE}.{target}"


# 상태 상수
API_KEY_ACTIVE = "ACTIVE"
API_KEY_DISABLED = "DISABLED"


class AdminAccount(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "admin_account"
    __table_args__ = _SCHEMA

    login_id: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))


class CollectorApiKey(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "collector_api_key"
    __table_args__ = _SCHEMA

    name: Mapped[str] = mapped_column(String(200))
    api_key_hash: Mapped[str] = mapped_column(String(128), index=True)
    api_key_masked: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default=API_KEY_ACTIVE, server_default=API_KEY_ACTIVE)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    llm: Mapped["ApiKeyLlmConfig"] = relationship(
        back_populates="api_key", uselist=False, cascade="all, delete-orphan"
    )
    embedding: Mapped["ApiKeyEmbeddingConfig"] = relationship(
        back_populates="api_key", uselist=False, cascade="all, delete-orphan"
    )
    db_connections: Mapped[list["ApiKeyDbConnection"]] = relationship(
        back_populates="api_key", cascade="all, delete-orphan"
    )


class ApiKeyLlmConfig(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "api_key_llm_config"
    __table_args__ = _SCHEMA

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_fk("collector_api_key.id"), ondelete="CASCADE"), unique=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="openai", server_default="openai")
    endpoint: Mapped[str] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(200))
    secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)

    api_key: Mapped[CollectorApiKey] = relationship(back_populates="llm")


class ApiKeyEmbeddingConfig(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "api_key_embedding_config"
    __table_args__ = _SCHEMA

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_fk("collector_api_key.id"), ondelete="CASCADE"), unique=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="openai", server_default="openai")
    endpoint: Mapped[str] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(200))
    secret_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    dimension: Mapped[int] = mapped_column(Integer, default=1536, server_default="1536")

    api_key: Mapped[CollectorApiKey] = relationship(back_populates="embedding")


class ApiKeyDbConnection(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "api_key_db_connection"
    __table_args__ = _SCHEMA

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_fk("collector_api_key.id"), ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=5432, server_default="5432")
    database: Mapped[str] = mapped_column(String(200))
    username: Mapped[str] = mapped_column(String(200))
    password_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    api_key: Mapped[CollectorApiKey] = relationship(back_populates="db_connections")


class ApiKeyUsageHistory(UuidPkMixin, Base):
    __tablename__ = "api_key_usage_history"
    __table_args__ = _SCHEMA

    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_fk("collector_api_key.id"), ondelete="CASCADE")
    )
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    request_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    response_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    endpoint: Mapped[str | None] = mapped_column(String(200), nullable=True)


class DbMigrationHistory(UuidPkMixin, Base):
    __tablename__ = "db_migration_history"
    __table_args__ = _SCHEMA

    host: Mapped[str] = mapped_column(String(255))
    database: Mapped[str] = mapped_column(String(200))
    target_schemas: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS", server_default="SUCCESS")
    migrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisJob(UuidPkMixin, Base):
    """검토 전 임시 분석 결과 staging. 사용자 DB가 아닌 수집기 운영 DB에 둔다.

    register 시 status=RUNNING 행을 먼저 만들고 job_id를 즉시 반환한 뒤,
    백그라운드 태스크가 파이프라인을 실행하며 current_step/current_file_index를 갱신한다.
    완료 시 result_json을 채우고 status=COMPLETED로 바꾼다. review에서 조회,
    save 시 사용자 DB(report_origin_data/report_chunk_data)로 영속화한 뒤 삭제한다.
    """

    __tablename__ = "analysis_job"
    __table_args__ = _SCHEMA

    report_type_code: Mapped[str] = mapped_column(String(100))
    chunk_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    # [{fileId,fileName,title,summary,chunks:[{order,text,embedding,keywords,keywordsText}],
    #   results:[{type,title,preview,content}]}]
    result_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # 진행 상태 추적 (폴링 UI용). status: RUNNING/COMPLETED/FAILED,
    # current_step: EXTRACT/SUMMARY/CHUNK/EMBEDDING/SKILL/DONE (대문자 = FE 단계 키)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING", server_default="RUNNING")
    total_files: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    current_file_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    current_file_name: Mapped[str] = mapped_column(String(500), default="", server_default="")
    current_step: Mapped[str] = mapped_column(String(20), default="EXTRACT", server_default="EXTRACT")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnalysisResult(UuidPkMixin, Base):
    """저장된 원본 데이터의 분석 결과(SUMMARY/TOC/STYLE 등). 운영 DB에 영속한다.

    origin_data_id는 사용자 DB `data_collector.report_origin_data.id`를 가리키지만
    서로 다른 DB라 물리 FK는 두지 않는다(값 참조).
    """

    __tablename__ = "analysis_result"
    __table_args__ = _SCHEMA

    origin_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(300))
    preview: Mapped[str] = mapped_column(String, default="", server_default="")
    content: Mapped[str] = mapped_column(String, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminAuditLog(UuidPkMixin, Base):
    __tablename__ = "admin_audit_log"
    __table_args__ = _SCHEMA

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(_fk("admin_account.id"), ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
