from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.user_db import UserDbParams, get_user_engine
from app.db.user_schema import apply_migration, needs_migration
from app.models.collector import DbMigrationHistory
from app.schemas.db_connection import DbConnectionTestRequest, DbTestResultOut
from app.services import db_credential_stage


def _params(req: DbConnectionTestRequest) -> UserDbParams:
    return UserDbParams(
        host=req.host,
        port=req.port,
        database=req.database,
        username=req.username,
        password=req.password,
    )


async def test_connection(req: DbConnectionTestRequest) -> DbTestResultOut:
    """실제 접속을 시도하고, 성공 시 필수 스키마 존재 여부로 마이그레이션 필요 여부를 판정."""
    params = _params(req)
    engine = get_user_engine(params)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return DbTestResultOut(ok=False, needs_migration=False)

    need = await needs_migration(engine)
    # 저장 단계에서 재사용하도록 비밀번호를 잠시 보관
    db_credential_stage.stage(req.host, req.port, req.database, req.username, req.password)
    return DbTestResultOut(ok=True, needs_migration=need)


async def migrate(req: DbConnectionTestRequest, collector_db: AsyncSession) -> None:
    """대상 사용자 DB에 스키마/테이블 생성 후, collector DB에 이력 기록."""
    params = _params(req)
    engine = get_user_engine(params)
    await apply_migration(engine)
    db_credential_stage.stage(req.host, req.port, req.database, req.username, req.password)

    collector_db.add(
        DbMigrationHistory(
            host=req.host,
            database=req.database,
            target_schemas="data_collector,jarvis",
            status="SUCCESS",
        )
    )
    await collector_db.commit()
