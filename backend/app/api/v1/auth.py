from fastapi import APIRouter
from pydantic import BaseModel

from app.core.security import create_access_token
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login")
async def login(payload: LoginRequest) -> ApiResponse[LoginResponse]:
    # TODO: collector_service.collector_api_key 조회 및 만료/비활성 여부 검증 (정책 문서 1.2)
    token = create_access_token(subject=payload.api_key)
    return ApiResponse.success(LoginResponse(access_token=token))
