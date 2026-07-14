from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import UserContext, get_user_context
from app.schemas.common import ApiResponse
from app.schemas.data import DataRegisterPayload, FileReviewOut, JobProgressOut, RawDataOut
from app.services import data_service
from app.services.errors import NotFoundError

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}/progress")
async def get_progress(
    job_id: str, collector: AsyncSession = Depends(get_db)
) -> ApiResponse[JobProgressOut]:
    """분석 진행 상태 폴링용. UUID가 capability이므로 review와 동일하게 무인증."""
    try:
        job = await data_service.get_progress(collector, job_id)
    except NotFoundError as exc:
        # save 완료 후 job이 삭제된 경우 등: FE가 종료로 처리하도록 실패 응답.
        return ApiResponse.failure(str(exc))
    return ApiResponse.success(
        JobProgressOut(
            status=job.status,
            total_files=job.total_files,
            current_file_index=job.current_file_index,
            current_file_name=job.current_file_name,
            current_step=job.current_step,
            error_message=job.error_message,
        )
    )


@router.get("/{job_id}/review")
async def get_review(
    job_id: str, collector: AsyncSession = Depends(get_db)
) -> ApiResponse[list[FileReviewOut]]:
    try:
        return ApiResponse.success(await data_service.get_review(collector, job_id))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


@router.post("/{job_id}/save")
async def save_data(
    job_id: str,
    payload: DataRegisterPayload,  # FE가 함께 보내지만 결과는 job에 저장되어 있어 참고용
    ctx: UserContext = Depends(get_user_context),
) -> ApiResponse[list[RawDataOut]]:
    try:
        return ApiResponse.success(await data_service.save_data(ctx, job_id))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))
