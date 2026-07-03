import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/data", tags=["data"])


class DataRegisterRequest(BaseModel):
    file_id: str
    report_type: str | None = None


class DataRegisterResponse(BaseModel):
    job_id: str


async def _run_analysis_pipeline(job_id: str, file_id: str) -> None:
    # TODO: 원문 추출 -> Summary -> Chunk -> Embedding -> Report Skill 생성 (정책 문서 5.1)
    # LangChain/LangGraph Agent 실행 및 Job 상태 갱신은 app/tasks, app/agents 에서 구현 예정
    pass


@router.post("/", dependencies=[Depends(get_current_token_payload)])
async def register_data(
    payload: DataRegisterRequest, background_tasks: BackgroundTasks
) -> ApiResponse[DataRegisterResponse]:
    job_id = str(uuid.uuid4())

    # TODO: 데이터 등록 요청을 사용자 DB에 저장 후 Job 상태를 WAITING으로 기록
    background_tasks.add_task(_run_analysis_pipeline, job_id, payload.file_id)

    return ApiResponse.success(DataRegisterResponse(job_id=job_id))
