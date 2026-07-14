"""collector_service tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "collector_service"

_UUID = postgresql.UUID(as_uuid=True)
_UUID_PK = sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # 이미 이 마이그레이션의 테이블이 존재하면 재생성하지 않는다.
    # 0002 테이블은 한 트랜잭션에서 원자적으로 생성되므로 admin_account 존재 여부를
    # 대표 지표로 삼는다. (버전 기록만 유실된 드리프트 등에서 재실행 시 충돌 방지)
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("admin_account", schema=SCHEMA):
        return

    op.create_table(
        "admin_account",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("login_id", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        *_timestamps(),
        schema=SCHEMA,
    )

    op.create_table(
        "collector_api_key",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key_hash", sa.String(128), nullable=False),
        sa.Column("api_key_masked", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_collector_api_key_api_key_hash", "collector_api_key", ["api_key_hash"], schema=SCHEMA
    )

    op.create_table(
        "api_key_llm_config",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "api_key_id", _UUID,
            sa.ForeignKey(f"{SCHEMA}.collector_api_key.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("secret_encrypted", sa.String(), nullable=True),
        *_timestamps(),
        schema=SCHEMA,
    )

    op.create_table(
        "api_key_embedding_config",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "api_key_id", _UUID,
            sa.ForeignKey(f"{SCHEMA}.collector_api_key.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False, server_default="openai"),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("secret_encrypted", sa.String(), nullable=True),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="1536"),
        *_timestamps(),
        schema=SCHEMA,
    )

    op.create_table(
        "api_key_db_connection",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "api_key_id", _UUID,
            sa.ForeignKey(f"{SCHEMA}.collector_api_key.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="5432"),
        sa.Column("database", sa.String(200), nullable=False),
        sa.Column("username", sa.String(200), nullable=False),
        sa.Column("password_encrypted", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        *_timestamps(),
        schema=SCHEMA,
    )

    op.create_table(
        "api_key_usage_history",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "api_key_id", _UUID,
            sa.ForeignKey(f"{SCHEMA}.collector_api_key.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("request_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("endpoint", sa.String(200), nullable=True),
        schema=SCHEMA,
    )

    op.create_table(
        "db_migration_history",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("database", sa.String(200), nullable=False),
        sa.Column("target_schemas", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUCCESS"),
        sa.Column("migrated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "analysis_job",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_type_code", sa.String(100), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        # 진행 상태 추적 (폴링 UI용)
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_file_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("current_step", sa.String(20), nullable=False, server_default="EXTRACT"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )

    op.create_table(
        "analysis_result",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("origin_data_id", _UUID, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("preview", sa.String(), nullable=False, server_default=""),
        sa.Column("content", sa.String(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_analysis_result_origin_data_id", "analysis_result", ["origin_data_id"], schema=SCHEMA
    )

    op.create_table(
        "admin_audit_log",
        sa.Column("id", _UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "admin_id", _UUID,
            sa.ForeignKey(f"{SCHEMA}.admin_account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )


def downgrade() -> None:
    for table in (
        "admin_audit_log",
        "analysis_result",
        "analysis_job",
        "db_migration_history",
        "api_key_usage_history",
        "api_key_db_connection",
        "api_key_embedding_config",
        "api_key_llm_config",
        "collector_api_key",
        "admin_account",
    ):
        op.drop_table(table, schema=SCHEMA)
