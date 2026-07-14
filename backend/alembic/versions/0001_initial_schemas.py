"""initial schemas and extensions

Revision ID: 0001
Revises:
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 서버 startup 마이그레이션 대상은 서비스 자체 DB(collector_service)뿐이다.
# jarvis / data_collector 스키마와 vector 확장은 사용자 연결 DB 전용이라
# app/db/user_schema.py(migrate 엔드포인트)에서 생성한다.
SCHEMAS = ("collector_service",)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def downgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
