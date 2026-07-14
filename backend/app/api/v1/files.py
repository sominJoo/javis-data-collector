from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_user_db
from app.schemas.common import ApiResponse
from app.schemas.data import FileUploadOut
from app.services import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("")
async def upload_file(
    file: UploadFile, db: AsyncSession = Depends(get_user_db)
) -> ApiResponse[FileUploadOut]:
    content = await file.read()
    file_id = await file_service.save_upload(
        db, file.filename or "upload", content, file.content_type
    )
    return ApiResponse.success(FileUploadOut(file_id=file_id))
