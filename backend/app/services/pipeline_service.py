import re
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.document_analysis_agent import document_analysis_agent
from app.core import crypto
from app.core.config import get_settings
from app.models.collector import CollectorApiKey
from app.schemas.data import UploadedFileSchema
from app.services import file_service
from app.services.llm import EmbeddingSpec, LlmSpec

# 노드 완료 → 다음 활성 단계(FE 단계 키). skill 완료는 파일 종료라 매핑 없음.
_NODE_NEXT_STEP = {
    "extract": "SUMMARY",
    "summary": "CHUNK",
    "chunk": "EMBEDDING",
    "embedding": "SKILL",
}

# on_step(file_index, file_name, step_key): 현재 활성 단계를 알린다.
ProgressCallback = Callable[[int, str, str], Awaitable[None]]


def llm_spec(api_key: CollectorApiKey) -> LlmSpec:
    cfg = api_key.llm
    secret = crypto.decrypt(cfg.secret_encrypted) if cfg.secret_encrypted else None
    return LlmSpec(endpoint=cfg.endpoint, model=cfg.model, secret=secret)


def embed_spec(api_key: CollectorApiKey) -> EmbeddingSpec:
    cfg = api_key.embedding
    secret = crypto.decrypt(cfg.secret_encrypted) if cfg.secret_encrypted else None
    # per-key 모델 우선, 없으면 전역 EMBEDDING_MODEL로 fallback.
    model = cfg.model or get_settings().embedding_model
    return EmbeddingSpec(
        endpoint=cfg.endpoint, model=model, dimension=cfg.dimension, secret=secret
    )


def _strip_ext(name: str) -> str:
    return re.sub(r"\.[^.]+$", "", name)


async def run_pipeline(
    files: list[UploadedFileSchema],
    report_type_name: str,
    skills: list[dict[str, Any]],
    chunk_count: int,
    spec: LlmSpec,
    embed_spec: EmbeddingSpec,
    session: AsyncSession | None = None,
    report_type_detail: str = "",
    on_step: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    """파일별로 분석 그래프를 실행해 검토용 결과 리스트를 만든다.

    session이 주어지면 file_id로 실제 저장 경로를 해석해 원문 파싱에 사용한다.
    report_type_detail은 스킬 추출(목차 등) 프롬프트에 참고 컨텍스트로 전달한다.
    on_step은 각 파일에서 활성 단계가 바뀔 때마다 호출된다(폴링 UI 진행 표시용).
    astream(updates)로 노드 완료 이벤트를 받아 최종 상태를 직접 누적한다.
    """
    out: list[dict[str, Any]] = []
    for idx, f in enumerate(files):
        if on_step:
            await on_step(idx, f.name, "EXTRACT")
        file_path = await file_service.get_storage_path(session, f.id) if session else None
        state = {
            "file_name": f.name,
            "file_path": file_path or "",
            "title": _strip_ext(f.name),
            "report_type_name": report_type_name,
            "report_type_detail": report_type_detail,
            "skills": skills,
            "chunk_count": chunk_count,
            "llm": spec,
            "embed": embed_spec,
        }
        final: dict[str, Any] = {}
        async for event in document_analysis_agent.astream(state, stream_mode="updates"):
            for node_name, update in event.items():
                if update:
                    final.update(update)  # 노드는 overwrite dict만 반환(reducer 없음)
                nxt = _NODE_NEXT_STEP.get(node_name)
                if nxt and on_step:
                    await on_step(idx, f.name, nxt)
        out.append(
            {
                "fileId": f.id,
                "fileName": f.name,
                "title": _strip_ext(f.name),
                "reporter": final.get("reporter", ""),
                "summary": final.get("summary", ""),
                "chunks": final.get("chunks", []),
                "results": final.get("results", []),
            }
        )
    return out


async def rerun_analysis(
    title: str,
    content: str,
    report_type_name: str,
    skills: list[dict[str, Any]],
    chunk_count: int,
    spec: LlmSpec,
    embed_spec: EmbeddingSpec,
    report_type_detail: str = "",
) -> dict[str, Any]:
    """저장된 원문(content)으로 분석 그래프를 다시 실행한다(스킬 재추출 포함).

    원본 파일 링크가 없어도 저장된 청크 텍스트를 원문으로 재사용한다.
    embedding 노드를 거치므로 반환 chunks에 embedding/keywords가 포함된다.
    """
    final = await document_analysis_agent.ainvoke(
        {
            "file_name": title,
            "file_path": "",
            "text": content,
            "title": title,
            "report_type_name": report_type_name,
            "report_type_detail": report_type_detail,
            "skills": skills,
            "chunk_count": chunk_count,
            "llm": spec,
            "embed": embed_spec,
        }
    )
    return {
        "title": title,
        "reporter": final.get("reporter", ""),
        "summary": final.get("summary", ""),
        "chunks": final.get("chunks", []),
        "results": final.get("results", []),
    }
