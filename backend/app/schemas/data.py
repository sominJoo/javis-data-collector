from datetime import datetime

from app.schemas.base import CamelModel


class UploadedFileSchema(CamelModel):
    id: str
    name: str
    size: str = ""


class DataRegisterPayload(CamelModel):
    report_type_code: str
    files: list[UploadedFileSchema] = []
    chunk_count: int = 1


class RegisterResponse(CamelModel):
    job_id: str


class FileUploadOut(CamelModel):
    file_id: str


class AnalysisResultSchema(CamelModel):
    type: str
    title: str
    preview: str = ""
    content: str = ""


class ChunkSchema(CamelModel):
    order: int
    text: str


class RawDataOut(CamelModel):
    id: str
    title: str
    file_name: str
    report_type_code: str
    report_type_name: str
    chunk_count: int
    created_at: datetime
    status: str


class RawDataListOut(CamelModel):
    total: int  # 현재 필터·검색 조건에 해당하는 전체 건수(페이지네이션 대비)
    items: list[RawDataOut] = []


class RawDataDetailOut(RawDataOut):
    summary: str = ""
    chunks: list[ChunkSchema] = []
    results: list[AnalysisResultSchema] = []


class DataStatsOut(CamelModel):
    total: int
    done: int
    ing: int
    chunks: int


class FileReviewOut(CamelModel):
    file_id: str
    file_name: str
    results: list[AnalysisResultSchema] = []


class JobProgressOut(CamelModel):
    status: str  # RUNNING / COMPLETED / FAILED
    total_files: int
    current_file_index: int
    current_file_name: str = ""
    current_step: str  # EXTRACT / SUMMARY / CHUNK / EMBEDDING / SKILL / DONE
    error_message: str | None = None
