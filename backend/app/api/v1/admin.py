from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.api_key import ApiKeyIn, ApiKeyOut
from app.schemas.common import ApiResponse
from app.schemas.db_connection import DbConnectionTestRequest, DbTestResultOut
from app.services import api_key_service, db_connection_service
from app.services.api_key_service import NotFoundError

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- API Keys ----------
@router.get("/api-keys")
async def list_api_keys(db: AsyncSession = Depends(get_db)) -> ApiResponse[list[ApiKeyOut]]:
    return ApiResponse.success(await api_key_service.list_api_keys(db))


@router.post("/api-keys")
async def create_api_key(
    payload: ApiKeyIn, db: AsyncSession = Depends(get_db)
) -> ApiResponse[ApiKeyOut]:
    return ApiResponse.success(await api_key_service.create_api_key(db, payload))


@router.put("/api-keys/{key_id}")
async def update_api_key(
    key_id: str, payload: ApiKeyIn, db: AsyncSession = Depends(get_db)
) -> ApiResponse[ApiKeyOut]:
    try:
        return ApiResponse.success(await api_key_service.update_api_key(db, key_id, payload))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


@router.post("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: str, db: AsyncSession = Depends(get_db)
) -> ApiResponse[None]:
    try:
        await api_key_service.toggle_api_key(db, key_id)
        return ApiResponse.success(None)
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


# ---------- DB Connections ----------
@router.post("/db-connections/test")
async def test_db_connection(
    payload: DbConnectionTestRequest,
) -> ApiResponse[DbTestResultOut]:
    return ApiResponse.success(await db_connection_service.test_connection(payload))


@router.post("/db-connections/migrate")
async def migrate_db_connection(
    payload: DbConnectionTestRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[None]:
    await db_connection_service.migrate(payload, db)
    return ApiResponse.success(None)
