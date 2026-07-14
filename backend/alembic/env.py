import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.models.base import Base

config = context.config

if config.config_file_name is not None:
    # 앱과 같은 프로세스(startup lifespan)에서 alembic을 실행하므로, 기본값
    # disable_existing_loggers=True는 이미 생성된 app.* 로거를 전부 비활성화한다.
    # (마이그레이션 이후 app 로그가 콘솔에 안 찍히는 원인) → False로 유지한다.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# alembic 버전 기록(alembic_version)을 서비스 스키마 안에 둔다.
# public에 두면 collector_service 스키마를 드롭해도 버전 포인터가 남아
# "버전은 0002인데 테이블은 없음" 같은 드리프트가 생긴다. 스키마 안에 두면
# 스키마 드롭 시 버전 기록도 함께 사라져 실제 상태와 항상 일치한다.
VERSION_TABLE_SCHEMA = "collector_service"


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=VERSION_TABLE_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=VERSION_TABLE_SCHEMA,
    )

    # 버전 테이블을 만들려면 대상 스키마가 먼저 존재해야 한다(첫 마이그레이션이
    # 스키마를 만들기 전에 alembic이 버전 테이블 생성을 시도하므로 부트스트랩).
    # 반드시 alembic 트랜잭션 '안'에서 만들어야 한다. 밖에서 실행하면 커밋되지 않은
    # 트랜잭션이 열려, alembic이 커밋하지 않는 그 트랜잭션과 함께 전체가 롤백된다.
    with context.begin_transaction():
        connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{VERSION_TABLE_SCHEMA}"')
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
