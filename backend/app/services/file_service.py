"""업로드 파일 저장/조회.

바이트는 로컬 스토리지(`file_storage_path`)에 `{file_id}_{filename}`로 저장하고,
경로 메타데이터는 사용자 DB `jarvis.file`에 기록한다.
"""
import re
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user_data import File

_UNSAFE_NAME_RE = re.compile(r"[^\w.\-가-힣]+")


def _safe_name(name: str) -> str:
    """경로 구분자 등 위험 문자를 제거한 저장용 파일명."""
    cleaned = _UNSAFE_NAME_RE.sub("_", Path(name).name).strip("_")
    return cleaned or "upload"


def _ext(name: str) -> str:
    return Path(name).suffix.lstrip(".").lower()


async def save_upload(
    session: AsyncSession, filename: str, content: bytes, content_type: str | None = None
) -> str:
    """파일을 스토리지에 저장하고 메타데이터를 기록한 뒤 file_id를 반환한다."""
    file_id = str(uuid.uuid4())
    storage_dir = get_settings().storage_root  # cwd 무관 절대경로
    storage_dir.mkdir(parents=True, exist_ok=True)
    destination = storage_dir / f"{file_id}_{_safe_name(filename)}"
    destination.write_bytes(content)

    ext = _ext(filename)
    session.add(
        File(
            id=file_id,
            thread_id="",  # data-collector 업로드는 채팅 스레드에 속하지 않는다
            file_name=filename,
            file_size=len(content),
            file_type=ext.upper() or "UNKNOWN",
            mime_type=content_type,
            file_ext=ext or None,
            storage_path=str(destination),
            status="UPLOADED",
        )
    )
    await session.commit()
    return file_id


async def get_storage_path(session: AsyncSession, file_id: str) -> str | None:
    """file_id로 저장 경로를 조회한다. 없는 id면 None.

    과거에 상대경로로 저장된 레코드나 cwd 변동으로 원경로가 없으면
    storage_root(절대경로) 기준으로 파일명을 재해석해 반환한다.
    """
    f = await session.get(File, file_id)
    if f is None or not f.storage_path:
        return None
    p = Path(f.storage_path)
    if p.exists():
        return str(p)
    # 상대경로 저장분/이동분 방어: 저장 루트 하위에서 같은 파일명을 찾는다.
    candidate = get_settings().storage_root / p.name
    if candidate.exists():
        return str(candidate)
    return str(p)  # 원본 값 반환 (파싱 단계에서 실패로 로깅됨)
