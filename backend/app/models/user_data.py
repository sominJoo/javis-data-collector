"""사용자 DB(각 API Key의 기본 연결) 스키마 모델.

`jarvis` + `data_collector` 스키마에 파일·청크·보고서 원본/청크·보고서 유형을 저장한다.
collector Alembic 체인과 분리하기 위해 별도 MetaData(`UserBase`)를 사용하며,
migrate 엔드포인트가 대상 사용자 DB engine에 `create_all`로 적용한다.

컬럼/타입/기본값은 운영 jarvis·data_collector 스키마 DDL과 1:1로 일치시킨다.
- jarvis.*      : id `varchar(36)` (text UUID), `timestamp`(without time zone)
- data_collector.* : id `uuid`, `timestamptz`(with time zone) 기본
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Integer,
    MetaData,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.base import NAMING_CONVENTION

DATA_COLLECTOR = "data_collector"
JARVIS = "jarvis"

# 임베딩 벡터 차원 (embedding config dimension 기본값과 일치해야 함)
EMBEDDING_DIM = 1536


class UserBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---- id/타임스탬프 헬퍼 ---------------------------------------------------
def _text_pk() -> Mapped[str]:
    """jarvis.* : varchar(36) PK, gen_random_uuid()::text 기본값."""
    return mapped_column(
        String(36), primary_key=True, server_default=text("(gen_random_uuid())::text")
    )


def _uuid_pk() -> Mapped[uuid.UUID]:
    """data_collector.* : uuid PK, gen_random_uuid() 기본값."""
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def _ts(*, tz: bool, nullable: bool = False, onupdate: bool = False) -> Mapped[datetime]:
    col = mapped_column(
        DateTime(timezone=tz),
        server_default=func.now(),
        nullable=nullable,
        onupdate=func.now() if onupdate else None,
    )
    return col


# ==========================================================================
# jarvis 스키마 (id: varchar(36), timestamp without time zone)
# ==========================================================================
class File(UserBase):
    __tablename__ = "file"
    __table_args__ = {"schema": JARVIS}

    id: Mapped[str] = _text_pk()
    thread_id: Mapped[str] = mapped_column(String(36))
    file_name: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_type: Mapped[str] = mapped_column(String(30), server_default="UNKNOWN")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(20), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), server_default="UPLOADED")
    created_at: Mapped[datetime] = _ts(tz=False)
    updated_at: Mapped[datetime] = _ts(tz=False, onupdate=True)


class FileChunk(UserBase):
    __tablename__ = "file_chunk"
    __table_args__ = {"schema": JARVIS}

    id: Mapped[str] = _text_pk()
    file_id: Mapped[str] = mapped_column(String(36))
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime | None] = _ts(tz=False, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FileClassificationType(UserBase):
    __tablename__ = "file_classification_type"
    __table_args__ = {"schema": JARVIS}

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    created_at: Mapped[datetime] = _ts(tz=False)


class FileMetadata(UserBase):
    __tablename__ = "file_metadata"
    __table_args__ = {"schema": JARVIS}

    id: Mapped[str] = _text_pk()
    file_id: Mapped[str] = mapped_column(String(36))
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = _ts(tz=False)
    updated_at: Mapped[datetime] = _ts(tz=False, onupdate=True)


class FilePageText(UserBase):
    __tablename__ = "file_page_text"
    __table_args__ = {"schema": JARVIS}

    id: Mapped[str] = _text_pk()
    file_id: Mapped[str] = mapped_column(String(36))
    page_num: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = _ts(tz=False, nullable=True)


# ==========================================================================
# data_collector 스키마 (id: uuid, timestamptz)
# ==========================================================================
class ReportType(UserBase):
    __tablename__ = "report_type"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = _ts(tz=True)
    updated_at: Mapped[datetime] = _ts(tz=True, onupdate=True)


class ReportTypeSkill(UserBase):
    __tablename__ = "report_type_skill"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = _ts(tz=True)
    updated_at: Mapped[datetime] = _ts(tz=True, onupdate=True)


class ReportTypeSkillMapping(UserBase):
    __tablename__ = "report_type_skill_mapping"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    report_type_skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = _ts(tz=True)
    updated_at: Mapped[datetime] = _ts(tz=True, onupdate=True)


class ReportTypeRequiredInput(UserBase):
    __tablename__ = "report_type_required_input"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    classification_code: Mapped[str] = mapped_column(String(50))
    min_count: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = _ts(tz=True)


class ReportTypeOriginDataMapping(UserBase):
    __tablename__ = "report_type_origin_data_mapping"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    report_origin_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _ts(tz=True)


class ReportSkill(UserBase):
    __tablename__ = "report_skill"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = _ts(tz=True)
    updated_at: Mapped[datetime] = _ts(tz=True, onupdate=True)


class ReportOriginDataSkill(UserBase):
    __tablename__ = "report_origin_data_skill"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_origin_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = _ts(tz=True)
    updated_at: Mapped[datetime] = _ts(tz=True, onupdate=True)


class ReportOriginData(UserBase):
    __tablename__ = "report_origin_data"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(Text)
    reporter: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    images: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)


_MECAB_TSV = (
    "("
    "  setweight(to_tsvector('korean'::regconfig, title), 'A'::\"char\")"
    "  || setweight(to_tsvector('korean'::regconfig, content), 'B'::\"char\")"
    ") || setweight("
    "  to_tsvector('korean'::regconfig, COALESCE(keywords_text, ''::text)), 'C'::\"char\""
    ")"
)


class ReportChunkData(UserBase):
    __tablename__ = "report_chunk_data"
    __table_args__ = {"schema": DATA_COLLECTOR}

    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    title: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    keywords: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    keywords_text: Mapped[str] = mapped_column(Text, server_default="")
    # 생성 컬럼: title(A)/content(B)/keywords_text(C) 가중치 tsvector.
    # 'korean' text search config(mecab)가 대상 DB에 존재해야 한다.
    mecab_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_MECAB_TSV, persisted=True), nullable=True
    )
