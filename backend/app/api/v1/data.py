from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_user_context, get_user_db
from app.schemas.common import ApiResponse
from app.schemas.data import (
    DataRegisterPayload,
    DataStatsOut,
    RawDataDetailOut,
    RawDataOut,
    RegisterResponse,
)
from app.services import data_service
from app.services.errors import NotFoundError

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_user_db)) -> ApiResponse[DataStatsOut]:
    return ApiResponse.success(await data_service.get_stats(db))


@router.get("")
async def list_raw_data(
    q: str | None = None, db: AsyncSession = Depends(get_user_db)
) -> ApiResponse[list[RawDataOut]]:
    return ApiResponse.success(await data_service.list_raw_data(db, q))


@router.post("")
async def register_data(
    payload: DataRegisterPayload, ctx: UserContext = Depends(get_user_context)
) -> ApiResponse[RegisterResponse]:
    try:
        job_id = await data_service.register(ctx, payload)
        return ApiResponse.success(RegisterResponse(job_id=job_id))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


@router.get("/{data_id}")
async def get_raw_data(
    data_id: str, ctx: UserContext = Depends(get_user_context)
) -> ApiResponse[RawDataDetailOut]:
    try:
        return ApiResponse.success(await data_service.get_raw_data(ctx, data_id))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


@router.delete("/{data_id}")
async def delete_raw_data(
    data_id: str, ctx: UserContext = Depends(get_user_context)
) -> ApiResponse[None]:
    await data_service.delete_raw_data(ctx, data_id)
    return ApiResponse.success(None)


@router.post("/{data_id}/reanalyze")
async def reanalyze(
    data_id: str, ctx: UserContext = Depends(get_user_context)
) -> ApiResponse[None]:
    try:
        await data_service.reanalyze(ctx, data_id)
        return ApiResponse.success(None)
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))
