"""운영 DB(collector_service) Alembic 마이그레이션 실행 헬퍼.

앱 startup(lifespan)에서 `alembic upgrade head`를 실행해 서비스 자체 DB 스키마를
항상 최신으로 맞춘다. 접속 URL은 alembic/env.py가 settings.database_url로 설정한다.
"""
import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger("app.migrations")

# backend/app/core/migrations.py → parents[2] = backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    # cwd와 무관하게 스크립트 위치를 절대경로로 고정
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    return cfg


def _upgrade_head() -> None:
    command.upgrade(_config(), "head")


async def upgrade_to_head() -> None:
    """운영 DB를 head 리비전으로 업그레이드.

    env.py가 online 모드에서 asyncio.run()을 호출하므로, 실행 중인 이벤트 루프와
    충돌하지 않도록 별도 스레드에서 돌린다(새 스레드에는 실행 중 루프가 없음).
    """
    logger.info("운영 DB 마이그레이션 시작 (alembic upgrade head)")
    await asyncio.to_thread(_upgrade_head)
    # alembic env.py의 fileConfig가 root 로거(핸들러/레벨)를 alembic.ini 설정으로
    # 덮어쓰므로, 앱 로깅을 다시 적용해 원래 레벨/핸들러를 복구한다.
    from app.core.logging import configure_logging

    configure_logging()
    logger.info("운영 DB 마이그레이션 완료")
