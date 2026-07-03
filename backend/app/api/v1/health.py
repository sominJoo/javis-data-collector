from fastapi import APIRouter

from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> ApiResponse[dict[str, str]]:
    return ApiResponse.success({"status": "ok"})
