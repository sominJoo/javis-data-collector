from enum import StrEnum

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatus(StrEnum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus


@router.get("/{job_id}", dependencies=[Depends(get_current_token_payload)])
async def get_job_status(job_id: str) -> ApiResponse[JobStatusResponse]:
    # TODO: 사용자 DB에서 Job 상태 조회 (설계 문서 5.2)
    return ApiResponse.success(JobStatusResponse(job_id=job_id, status=JobStatus.WAITING))
