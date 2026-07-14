from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_api_key, verify_password
from app.models.collector import API_KEY_ACTIVE, AdminAccount, CollectorApiKey
from app.schemas.auth import AdminLoginRequest, LoginRequest
from app.schemas.common import ApiResponse
from app.schemas.session import SessionOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[SessionOut]:
    key = await db.scalar(
        select(CollectorApiKey).where(CollectorApiKey.api_key_hash == hash_api_key(payload.api_key))
    )
    if key is None or key.status != API_KEY_ACTIVE:
        return ApiResponse.failure("유효하지 않거나 비활성화된 API Key입니다.")
    if key.expired_at is not None and key.expired_at < datetime.now(timezone.utc):
        return ApiResponse.failure("만료된 API Key입니다.")

    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(
        subject=str(key.id), extra_claims={"role": "user", "api_key_id": str(key.id)}
    )
    return ApiResponse.success(SessionOut(token=token, role="user", display_name=key.name))


@router.post("/admin-login")
async def admin_login(
    payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[SessionOut]:
    admin = await db.scalar(select(AdminAccount).where(AdminAccount.login_id == payload.id))
    if admin is None or not verify_password(payload.password, admin.password_hash):
        return ApiResponse.failure("아이디 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(
        subject=str(admin.id), extra_claims={"role": "admin", "admin_id": str(admin.id)}
    )
    return ApiResponse.success(
        SessionOut(token=token, role="admin", display_name=admin.display_name)
    )
