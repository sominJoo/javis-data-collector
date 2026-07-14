"""seed initial admin account

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-14

초기 관리자 계정을 데이터 마이그레이션으로 생성한다. 값은 환경변수
(INITIAL_ADMIN_ID / INITIAL_ADMIN_PASSWORD)에서 읽으며, 둘 중 하나라도
비어 있으면 생성을 건너뛴다. login_id는 unique이므로 ON CONFLICT로 idempotent.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings
from app.core.security import hash_password

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "collector_service"


def upgrade() -> None:
    settings = get_settings()
    admin_id = (settings.initial_admin_id or "").strip()
    admin_pw = settings.initial_admin_password or ""
    # 환경변수 미설정 시 기본 계정을 만들지 않는다.
    if not admin_id or not admin_pw:
        return

    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.admin_account (login_id, password_hash, display_name)
            VALUES (:login_id, :password_hash, :display_name)
            ON CONFLICT (login_id) DO NOTHING
            """
        ).bindparams(
            login_id=admin_id,
            password_hash=hash_password(admin_pw),
            display_name="관리자",
        )
    )


def downgrade() -> None:
    settings = get_settings()
    admin_id = (settings.initial_admin_id or "").strip()
    if not admin_id:
        return
    op.execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.admin_account WHERE login_id = :login_id"
        ).bindparams(login_id=admin_id)
    )
