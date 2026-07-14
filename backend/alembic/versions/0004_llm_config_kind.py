"""api_key llm/embedding config에 kind(LOCAL/CLOUD) 추가

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-14

per-key LLM/Embedding 연결 종류를 구분한다.
  - LOCAL: 사내/로컬 LLM(자격 불필요) — secret 없이도 실제 호출
  - CLOUD: 상용 LLM(시크릿 필요)
기존 행은 엔드포인트가 OpenAI가 아니면 LOCAL로 백필한다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "collector_service"
TABLES = ("api_key_llm_config", "api_key_embedding_config")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in TABLES:
        cols = {c["name"] for c in inspector.get_columns(table, schema=SCHEMA)}
        if "kind" in cols:
            continue  # 이미 존재하면 건너뜀(드리프트 시 재실행 안전)
        op.add_column(
            table,
            sa.Column("kind", sa.String(20), nullable=False, server_default="CLOUD"),
            schema=SCHEMA,
        )
        # 기존 행 백필: OpenAI 엔드포인트가 아니면 로컬로 간주한다.
        op.execute(
            f"UPDATE {SCHEMA}.{table} SET kind = 'LOCAL' "
            "WHERE endpoint NOT ILIKE '%api.openai.com%'"
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "kind", schema=SCHEMA)
