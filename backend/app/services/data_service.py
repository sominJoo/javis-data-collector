import asyncio
import logging
import uuid
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import deps
from app.core.database import AsyncSessionLocal
from app.core.deps import UserContext
from app.core.user_db import UserDbParams, user_session
from app.models.collector import AnalysisJob
from app.models.user_data import (
    ReportChunkData,
    ReportOriginData,
    ReportOriginDataSkill,
    ReportSkill,
    ReportType,
    ReportTypeOriginDataMapping,
)
from app.schemas.data import (
    AnalysisResultSchema,
    ChunkSchema,
    DataRegisterPayload,
    DataStatsOut,
    FileReviewOut,
    RawDataDetailOut,
    RawDataListOut,
    RawDataOut,
)
from app.services import llm, pipeline_service, report_type_service
from app.services.errors import NotFoundError
from app.services.llm import EmbeddingSpec, LlmSpec

logger = logging.getLogger(__name__)

# 백그라운드 분석 태스크 참조 보관(GC 방지). 완료 시 콜백으로 제거한다.
_BG_TASKS: set[asyncio.Task] = set()

# 문서에서 추출한 스킬로 취급해 사용자 DB report_skill에 등록할 결과 타입(SUMMARY 제외).
_SKILL_TYPES = {"TOC", "STYLE"}


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise NotFoundError("데이터를 찾을 수 없습니다.") from exc


def _raw_out(od: ReportOriginData, code: str, name: str, chunk_count: int) -> RawDataOut:
    return RawDataOut(
        id=str(od.id),
        title=od.title,
        file_name=od.title,  # 별도 file_name 컬럼 없음 → title 사용
        report_type_code=code,
        report_type_name=name,
        chunk_count=chunk_count,
        created_at=od.created_at,
        status="SUCCESS",
    )


# ---------- register → 백그라운드 파이프라인 → staging job(운영 DB) ----------
async def register(ctx: UserContext, payload: DataRegisterPayload) -> str:
    """RUNNING staging job을 먼저 만들고 job_id를 즉시 반환한다.

    실제 파이프라인은 백그라운드 태스크(_run_job)가 자체 세션으로 실행하며
    current_step/current_file_index를 갱신한다. FE는 /jobs/{id}/progress를 폴링한다.
    """
    if not payload.files:
        raise NotFoundError("파일을 추가하세요.")
    rt = await report_type_service.get_report_type(ctx.session, payload.report_type_code)  # NotFound
    skills = [{"name": s.name, "status": s.status, "content": s.content} for s in rt.skills]

    # 1) RUNNING job 행 생성·commit (백그라운드 태스크가 별도 세션으로 조회하므로 먼저 확정)
    job = AnalysisJob(
        report_type_code=payload.report_type_code,
        chunk_count=payload.chunk_count,
        status="RUNNING",
        total_files=len(payload.files),
        current_file_index=0,
        current_file_name=payload.files[0].name,
        current_step="EXTRACT",
    )
    ctx.collector.add(job)
    await ctx.collector.commit()
    job_id = job.id

    # 2) 요청 스코프에서 plain 값만 캡처(세션/ORM 객체 전달 금지). 평문 secret 포함 → 로그 금지.
    params = deps.user_db_params(ctx.api_key)
    llm_spec = pipeline_service.llm_spec(ctx.api_key)
    embed_spec = pipeline_service.embed_spec(ctx.api_key)

    # 3) 백그라운드 디스패치 후 즉시 반환
    task = asyncio.create_task(
        _run_job(
            job_id=job_id,
            params=params,
            llm_spec=llm_spec,
            embed_spec=embed_spec,
            report_type_name=rt.name,
            report_type_detail=rt.description or "",
            skills=skills,
            files=list(payload.files),
            chunk_count=payload.chunk_count,
        )
    )
    _BG_TASKS.add(task)
    task.add_done_callback(_BG_TASKS.discard)
    return str(job_id)


async def _run_job(
    job_id: uuid.UUID,
    params: UserDbParams,
    llm_spec: LlmSpec,
    embed_spec: EmbeddingSpec,
    report_type_name: str,
    report_type_detail: str,
    skills: list[dict[str, Any]],
    files: list[Any],
    chunk_count: int,
) -> None:
    """백그라운드에서 파이프라인을 실행하며 job 진행 상태를 갱신한다.

    요청 스코프 세션은 이미 닫혔으므로 collector/user DB 세션을 자체적으로 연다.
    예외는 전부 흡수해 FAILED로 기록한다(태스크 밖으로 전파 금지).
    """
    try:
        async with AsyncSessionLocal() as collector:

            async def on_step(idx: int, name: str, step: str) -> None:
                await collector.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.id == job_id)
                    .values(
                        current_file_index=idx,
                        current_file_name=name,
                        current_step=step,
                        updated_at=func.now(),
                    )
                )
                await collector.commit()

            async with user_session(params) as session:
                results = await pipeline_service.run_pipeline(
                    files,
                    report_type_name,
                    skills,
                    chunk_count,
                    llm_spec,
                    embed_spec,
                    session=session,
                    report_type_detail=report_type_detail,
                    on_step=on_step,
                )
            await collector.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == job_id)
                .values(
                    result_json=results,
                    status="COMPLETED",
                    current_step="DONE",
                    updated_at=func.now(),
                )
            )
            await collector.commit()
    except Exception:
        # 상세는 서버 로그로만. error_message는 무인증 진행 조회로 노출되므로 일반 메시지만 저장.
        logger.exception("분석 파이프라인 실패: job=%s", job_id)
        try:
            async with AsyncSessionLocal() as collector:
                await collector.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.id == job_id)
                    .values(
                        status="FAILED",
                        error_message="분석 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                        updated_at=func.now(),
                    )
                )
                await collector.commit()
        except Exception:
            logger.exception("job 실패 상태 기록 실패: job=%s", job_id)


async def get_progress(collector: AsyncSession, job_id: str) -> AnalysisJob:
    job = await collector.get(AnalysisJob, _parse_uuid(job_id))
    if job is None:
        raise NotFoundError("분석 작업을 찾을 수 없습니다.")
    return job


async def get_review(collector: AsyncSession, job_id: str) -> list[FileReviewOut]:
    job = await collector.get(AnalysisJob, _parse_uuid(job_id))
    if job is None:
        raise NotFoundError("분석 작업을 찾을 수 없습니다.")
    return [
        FileReviewOut(
            file_id=f["fileId"],
            file_name=f["fileName"],
            results=[AnalysisResultSchema(**r) for r in f.get("results", [])],
        )
        for f in (job.result_json or [])
    ]


async def _report_type_id(db: AsyncSession, code: str) -> uuid.UUID | None:
    return await db.scalar(select(ReportType.id).where(ReportType.code == code))


async def _persist_file(
    db: AsyncSession, file: dict[str, Any], rt_id: uuid.UUID | None, ctx: UserContext
) -> tuple[ReportOriginData, int]:
    """원본 데이터 + 청크 + report_type 매핑을 사용자 DB에 저장한다.

    청크 embedding/keywords는 분석 단계(embedding 노드)에서 이미 계산돼 있으므로 재사용한다.
    누락된 경우(구버전 job 등)에만 저장 시점에 임베딩을 폴백 생성한다.
    """
    chunks = file.get("chunks", [])
    texts = [c["text"] for c in chunks]
    vectors = [c.get("embedding") for c in chunks]
    if texts and any(v is None for v in vectors):
        vectors = await llm.embed(texts, pipeline_service.embed_spec(ctx.api_key))

    od = ReportOriginData(
        title=file["title"],
        reporter=file.get("reporter", ""),  # 파싱 시 추출
        content="\n".join(texts),
        summary=file.get("summary", ""),
        created_at=func.now(),
        updated_at=func.now(),
    )
    db.add(od)
    await db.flush()

    if rt_id is not None:
        db.add(ReportTypeOriginDataMapping(report_type_id=rt_id, report_origin_data_id=od.id))
    for c, vec in zip(chunks, vectors):
        db.add(
            ReportChunkData(
                report_id=od.id,
                title=file["title"],
                chunk_index=c["order"],
                content=c["text"],
                embedding=vec,
                keywords=c.get("keywords"),
                keywords_text=c.get("keywords_text", ""),
            )
        )
    return od, len(chunks)


async def _persist_skills(
    db: AsyncSession, origin_data_id: uuid.UUID, results: list[dict[str, Any]]
) -> None:
    """문서에서 추출한 스킬(TOC/STYLE)을 사용자 DB report_skill에 등록하고 원본과 연결한다."""
    for r in results:
        if r.get("type") not in _SKILL_TYPES:
            continue
        skill = ReportSkill(
            name=r.get("title", ""),
            type=r["type"],
            description=(r.get("preview") or None),
            content=r.get("content", ""),
        )
        db.add(skill)
        await db.flush()  # skill.id 발급
        db.add(ReportOriginDataSkill(report_origin_data_id=origin_data_id, skill_id=skill.id))


async def save_data(ctx: UserContext, job_id: str) -> list[RawDataOut]:
    db = ctx.session
    job = await ctx.collector.get(AnalysisJob, _parse_uuid(job_id))
    if job is None:
        raise NotFoundError("분석 작업을 찾을 수 없습니다.")

    rt_id = await _report_type_id(db, job.report_type_code)
    rt_name = await db.scalar(
        select(ReportType.name).where(ReportType.code == job.report_type_code)
    ) or job.report_type_code

    created: list[tuple[ReportOriginData, int, list[dict[str, Any]]]] = []
    for f in job.result_json or []:
        od, cnt = await _persist_file(db, f, rt_id, ctx)
        created.append((od, cnt, f.get("results", [])))
    await db.commit()  # 사용자 DB: 원본/청크/매핑 확정 (od.id 발급)

    out: list[RawDataOut] = []
    for od, cnt, results in created:
        await db.refresh(od)
        await _persist_skills(db, od.id, results)  # 사용자 DB: report_skill + 연결(분석 결과)
        out.append(_raw_out(od, job.report_type_code, rt_name, cnt))

    await db.commit()  # 사용자 DB: 스킬/연결 확정
    await ctx.collector.delete(job)
    await ctx.collector.commit()  # 운영 DB: staging job 삭제
    return out


# ---------- 조회/삭제/통계/재분석 ----------
_ORIGIN_QUERY = (
    select(
        ReportOriginData,
        ReportType.code,
        ReportType.name,
        select(func.count())
        .select_from(ReportChunkData)
        .where(ReportChunkData.report_id == ReportOriginData.id)
        .scalar_subquery()
        .label("chunk_count"),
    )
    .outerjoin(
        ReportTypeOriginDataMapping,
        ReportTypeOriginDataMapping.report_origin_data_id == ReportOriginData.id,
    )
    .outerjoin(ReportType, ReportType.id == ReportTypeOriginDataMapping.report_type_id)
)


# 목록/카운트 공통 조인(제목 검색 + 유형 필터). count는 원본 기준 distinct로 집계한다.
_COUNT_BASE = (
    select(func.count(func.distinct(ReportOriginData.id)))
    .select_from(ReportOriginData)
    .outerjoin(
        ReportTypeOriginDataMapping,
        ReportTypeOriginDataMapping.report_origin_data_id == ReportOriginData.id,
    )
    .outerjoin(ReportType, ReportType.id == ReportTypeOriginDataMapping.report_type_id)
)


async def list_raw_data(
    db: AsyncSession, query: str | None, report_type_code: str | None = None
) -> RawDataListOut:
    list_stmt = _ORIGIN_QUERY.order_by(ReportOriginData.created_at.desc())
    count_stmt = _COUNT_BASE
    q = (query or "").strip()
    if q:
        cond = ReportOriginData.title.ilike(f"%{q}%")
        list_stmt, count_stmt = list_stmt.where(cond), count_stmt.where(cond)
    rtc = (report_type_code or "").strip()
    if rtc:
        cond = ReportType.code == rtc  # 매핑된 유형만(미매핑 원본 제외)
        list_stmt, count_stmt = list_stmt.where(cond), count_stmt.where(cond)

    total = await db.scalar(count_stmt) or 0
    rows = (await db.execute(list_stmt)).all()
    items = [_raw_out(od, code or "", name or "", cnt) for od, code, name, cnt in rows]
    return RawDataListOut(total=total, items=items)


async def _load_results(db: AsyncSession, origin_data_id: uuid.UUID) -> list[AnalysisResultSchema]:
    """사용자 DB(data_collector)에서 이 원본에 연결된 분석 결과(스킬)를 조회한다.

    분석 결과는 report_skill에 저장되고 report_origin_data_skill로 원본과 연결된다.
    운영 DB(collector_service)에는 두지 않는다(사용자 DB 스키마만 사용).
    """
    rows = (
        await db.scalars(
            select(ReportSkill)
            .join(ReportOriginDataSkill, ReportOriginDataSkill.skill_id == ReportSkill.id)
            .where(ReportOriginDataSkill.report_origin_data_id == origin_data_id)
            .order_by(ReportOriginDataSkill.created_at, ReportSkill.type)
        )
    ).all()
    return [
        AnalysisResultSchema(
            type=s.type,
            title=s.name,
            preview=s.description or "",
            content=s.content or "",
        )
        for s in rows
    ]


async def get_raw_data(ctx: UserContext, data_id: str) -> RawDataDetailOut:
    db = ctx.session
    row = (
        await db.execute(_ORIGIN_QUERY.where(ReportOriginData.id == _parse_uuid(data_id)))
    ).first()
    if row is None:
        raise NotFoundError("데이터를 찾을 수 없습니다.")
    od, code, name, cnt = row
    chunks = (
        await db.scalars(
            select(ReportChunkData)
            .where(ReportChunkData.report_id == od.id)
            .order_by(ReportChunkData.chunk_index)
        )
    ).all()
    return RawDataDetailOut(
        **_raw_out(od, code or "", name or "", cnt).model_dump(),
        summary=od.summary or "",
        chunks=[ChunkSchema(order=c.chunk_index, text=c.content) for c in chunks],
        results=await _load_results(db, od.id),  # 사용자 DB(data_collector)에서 조회
    )


async def delete_raw_data(ctx: UserContext, data_id: str) -> None:
    db = ctx.session
    rid = _parse_uuid(data_id)
    # 사용자 DB: FK 미선언 스키마 → 자식 행을 명시적으로 제거
    await db.execute(delete(ReportChunkData).where(ReportChunkData.report_id == rid))
    await db.execute(
        delete(ReportTypeOriginDataMapping).where(
            ReportTypeOriginDataMapping.report_origin_data_id == rid
        )
    )
    # 문서 스킬 링크 + 스킬 엔티티 제거
    skill_ids = (
        await db.scalars(
            select(ReportOriginDataSkill.skill_id).where(
                ReportOriginDataSkill.report_origin_data_id == rid
            )
        )
    ).all()
    await db.execute(
        delete(ReportOriginDataSkill).where(ReportOriginDataSkill.report_origin_data_id == rid)
    )
    if skill_ids:
        await db.execute(delete(ReportSkill).where(ReportSkill.id.in_(skill_ids)))
    await db.execute(delete(ReportOriginData).where(ReportOriginData.id == rid))
    await db.commit()


async def get_stats(db: AsyncSession) -> DataStatsOut:
    total = await db.scalar(select(func.count()).select_from(ReportOriginData)) or 0
    chunks = await db.scalar(select(func.count()).select_from(ReportChunkData)) or 0
    # status 컬럼이 없어 진행중(ing) 개념은 없다 → 전량 완료로 집계
    return DataStatsOut(total=total, done=total, ing=0, chunks=chunks)


async def reanalyze(ctx: UserContext, data_id: str) -> None:
    """저장된 원문으로 분석 그래프를 재실행한다: 요약·청크·스킬 재추출 + 재임베딩."""
    db = ctx.session
    od = await db.get(ReportOriginData, _parse_uuid(data_id))
    if od is None:
        raise NotFoundError("데이터를 찾을 수 없습니다.")

    code = await db.scalar(
        select(ReportType.code)
        .join(
            ReportTypeOriginDataMapping,
            ReportTypeOriginDataMapping.report_type_id == ReportType.id,
        )
        .where(ReportTypeOriginDataMapping.report_origin_data_id == od.id)
    )
    skills: list[dict[str, Any]] = []
    rt_name, rt_detail = "", ""
    if code:
        rt = await report_type_service.get_report_type(db, code)
        rt_name, rt_detail = rt.name, rt.description
        skills = [{"name": s.name, "status": s.status, "content": s.content} for s in rt.skills]

    prev_count = await db.scalar(
        select(func.count()).select_from(ReportChunkData).where(ReportChunkData.report_id == od.id)
    )
    f = await pipeline_service.rerun_analysis(
        od.title,
        od.content or "",
        rt_name,
        skills,
        chunk_count=prev_count or 1,
        spec=pipeline_service.llm_spec(ctx.api_key),
        embed_spec=pipeline_service.embed_spec(ctx.api_key),
        report_type_detail=rt_detail,
    )

    # embedding 노드가 이미 청크별 벡터/키워드를 계산해 둠. 누락 시에만 폴백 임베딩.
    new_chunks = f.get("chunks", [])
    texts = [c["text"] for c in new_chunks]
    vectors = [c.get("embedding") for c in new_chunks]
    if texts and any(v is None for v in vectors):
        vectors = await llm.embed(texts, pipeline_service.embed_spec(ctx.api_key))

    od.summary = f.get("summary", "")
    if f.get("reporter"):
        od.reporter = f["reporter"]
    od.content = "\n".join(texts) or od.content
    od.updated_at = func.now()
    await db.execute(delete(ReportChunkData).where(ReportChunkData.report_id == od.id))
    await db.flush()
    for c, vec in zip(new_chunks, vectors):
        db.add(
            ReportChunkData(
                report_id=od.id,
                title=od.title,
                chunk_index=c["order"],
                content=c["text"],
                embedding=vec,
                keywords=c.get("keywords"),
                keywords_text=c.get("keywords_text", ""),
            )
        )
    # 사용자 DB 스킬 링크 교체(기존 링크·스킬 제거 후 재등록)
    old_skill_ids = (
        await db.scalars(
            select(ReportOriginDataSkill.skill_id).where(
                ReportOriginDataSkill.report_origin_data_id == od.id
            )
        )
    ).all()
    await db.execute(
        delete(ReportOriginDataSkill).where(ReportOriginDataSkill.report_origin_data_id == od.id)
    )
    if old_skill_ids:
        await db.execute(delete(ReportSkill).where(ReportSkill.id.in_(old_skill_ids)))
    await db.flush()
    await _persist_skills(db, od.id, f.get("results", []))
    await db.commit()
