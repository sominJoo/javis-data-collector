from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_user_context, get_user_db
from app.schemas.common import ApiResponse
from app.schemas.report_type import ReportTypeIn, ReportTypeOut, SkillGenerateRequest
from app.services import report_type_service
from app.services.errors import ConflictError, NotFoundError

router = APIRouter(prefix="/report-types", tags=["report-types"])


# 정적 경로를 먼저 선언해야 "/{code}" 가 이를 가로채지 않는다.
@router.get("/classification-types")
async def list_classification_types(
    db: AsyncSession = Depends(get_user_db),
) -> ApiResponse[list[str]]:
    return ApiResponse.success(await report_type_service.list_classification_types(db))


@router.post("/skills/generate")
async def generate_skill(
    payload: SkillGenerateRequest, ctx: UserContext = Depends(get_user_context)
) -> ApiResponse[str]:
    content = await report_type_service.generate_skill(payload, ctx.api_key.llm)
    return ApiResponse.success(content)


@router.get("")
async def list_report_types(
    db: AsyncSession = Depends(get_user_db),
) -> ApiResponse[list[ReportTypeOut]]:
    return ApiResponse.success(await report_type_service.list_report_types(db))


@router.post("")
async def create_report_type(
    payload: ReportTypeIn, db: AsyncSession = Depends(get_user_db)
) -> ApiResponse[ReportTypeOut]:
    try:
        return ApiResponse.success(await report_type_service.create_report_type(db, payload))
    except ConflictError as exc:
        return ApiResponse.failure(str(exc))


@router.get("/{code}")
async def get_report_type(
    code: str, db: AsyncSession = Depends(get_user_db)
) -> ApiResponse[ReportTypeOut]:
    try:
        return ApiResponse.success(await report_type_service.get_report_type(db, code))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))


@router.put("/{code}")
async def update_report_type(
    code: str, payload: ReportTypeIn, db: AsyncSession = Depends(get_user_db)
) -> ApiResponse[ReportTypeOut]:
    try:
        return ApiResponse.success(await report_type_service.update_report_type(db, code, payload))
    except NotFoundError as exc:
        return ApiResponse.failure(str(exc))
