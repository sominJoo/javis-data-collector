import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import get_current_token_payload
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/files", tags=["files"])


class FileUploadResponse(BaseModel):
    file_id: str


@router.post("/", dependencies=[Depends(get_current_token_payload)])
async def upload_file(file: UploadFile) -> ApiResponse[FileUploadResponse]:
    settings = get_settings()
    file_id = str(uuid.uuid4())

    storage_dir = Path(settings.file_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / f"{file_id}_{file.filename}"
    destination.write_bytes(await file.read())

    # TODO: 파일 메타데이터(storage_path 포함)를 사용자 DB에 저장 (설계 문서 1.6)
    return ApiResponse.success(FileUploadResponse(file_id=file_id))
