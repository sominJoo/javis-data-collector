from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.report_skill_agent import report_skill_agent
from app.core import crypto
from app.models.collector import ApiKeyLlmConfig
from app.models.user_data import (
    FileClassificationType,
    ReportType,
    ReportTypeRequiredInput,
    ReportTypeSkill,
    ReportTypeSkillMapping,
)
from app.schemas.report_type import (
    ReportSkillSchema,
    ReportTypeIn,
    ReportTypeOut,
    SkillGenerateRequest,
)
from app.services import llm
from app.services.errors import ConflictError, NotFoundError


async def _classification_codes(db: AsyncSession, rt_id) -> list[str]:
    rows = await db.scalars(
        select(ReportTypeRequiredInput.classification_code)
        .where(ReportTypeRequiredInput.report_type_id == rt_id)
        .order_by(ReportTypeRequiredInput.created_at)
    )
    return list(rows)


async def _skills(db: AsyncSession, rt_id) -> list[ReportTypeSkill]:
    """매핑을 경유해 이 report_type에 연결된 스킬을 생성 순서대로 반환."""
    rows = await db.scalars(
        select(ReportTypeSkill)
        .join(
            ReportTypeSkillMapping,
            ReportTypeSkillMapping.report_type_skill_id == ReportTypeSkill.id,
        )
        .where(ReportTypeSkillMapping.report_type_id == rt_id)
        .order_by(ReportTypeSkillMapping.created_at)
    )
    return list(rows)


def _skill_out(s: ReportTypeSkill) -> ReportSkillSchema:
    return ReportSkillSchema(
        skill_type=s.type,
        name=s.name,
        description=s.description or "",
        status="uploaded" if (s.content or "").strip() else "none",
        content=s.content or "",
    )


async def _to_out(db: AsyncSession, rt: ReportType) -> ReportTypeOut:
    return ReportTypeOut(
        code=rt.code,
        name=rt.name,
        description=rt.description or "",
        classification_types=await _classification_codes(db, rt.id),
        skills=[_skill_out(s) for s in await _skills(db, rt.id)],
        updated_at=rt.updated_at,
        active=rt.is_active,
    )


async def _get(db: AsyncSession, code: str) -> ReportType:
    rt = await db.scalar(select(ReportType).where(ReportType.code == code))
    if rt is None:
        raise NotFoundError("보고서 유형을 찾을 수 없습니다.")
    return rt


async def _replace_children(
    db: AsyncSession,
    rt: ReportType,
    classification_types: list[str],
    skills: list[ReportSkillSchema],
) -> None:
    """required_input + skill_mapping(+연결 스킬)을 지우고 새로 구성한다."""
    old_skill_ids = list(
        await db.scalars(
            select(ReportTypeSkillMapping.report_type_skill_id).where(
                ReportTypeSkillMapping.report_type_id == rt.id
            )
        )
    )
    await db.execute(
        delete(ReportTypeSkillMapping).where(ReportTypeSkillMapping.report_type_id == rt.id)
    )
    if old_skill_ids:
        await db.execute(delete(ReportTypeSkill).where(ReportTypeSkill.id.in_(old_skill_ids)))
    await db.execute(
        delete(ReportTypeRequiredInput).where(ReportTypeRequiredInput.report_type_id == rt.id)
    )
    await db.flush()

    for code in classification_types:
        db.add(ReportTypeRequiredInput(report_type_id=rt.id, classification_code=code))
    for s in skills:
        skill = ReportTypeSkill(
            name=s.name,
            type=s.skill_type,
            description=s.description,
            content=s.content or "",
        )
        db.add(skill)
        await db.flush()
        db.add(
            ReportTypeSkillMapping(report_type_id=rt.id, report_type_skill_id=skill.id)
        )


async def list_report_types(db: AsyncSession) -> list[ReportTypeOut]:
    rows = (await db.scalars(select(ReportType).order_by(ReportType.updated_at.desc()))).all()
    return [await _to_out(db, r) for r in rows]


async def get_report_type(db: AsyncSession, code: str) -> ReportTypeOut:
    return await _to_out(db, await _get(db, code))


async def create_report_type(db: AsyncSession, payload: ReportTypeIn) -> ReportTypeOut:
    if not payload.code.strip():
        raise ConflictError("Code를 입력하세요.")
    exists = await db.scalar(select(ReportType.id).where(ReportType.code == payload.code))
    if exists is not None:
        raise ConflictError("이미 존재하는 Code입니다.")

    rt = ReportType(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        is_active=payload.active,
    )
    db.add(rt)
    await db.flush()
    await _replace_children(db, rt, list(payload.classification_types), payload.skills)
    await db.commit()
    return await _to_out(db, await _get(db, payload.code))


async def update_report_type(db: AsyncSession, code: str, payload: ReportTypeIn) -> ReportTypeOut:
    rt = await _get(db, code)  # code는 경로 기준(불변)
    rt.name = payload.name
    rt.description = payload.description
    rt.is_active = payload.active
    await _replace_children(db, rt, list(payload.classification_types), payload.skills)
    await db.commit()
    return await _to_out(db, await _get(db, code))


async def list_classification_types(db: AsyncSession) -> list[str]:
    rows = (
        await db.scalars(
            select(FileClassificationType.name)
            .where(FileClassificationType.is_active.is_(True))
            .order_by(FileClassificationType.sort_order)
        )
    ).all()
    return list(rows)


async def generate_skill(req: SkillGenerateRequest, llm_cfg: ApiKeyLlmConfig) -> str:
    """보고서 타입 컨텍스트로 skill_type에 맞는 스킬 정의 문서를 생성한다.

    LLM 호출을 포함한 생성 로직은 report_skill_agent(LangGraph)가 수행한다.
    """
    secret = crypto.decrypt(llm_cfg.secret_encrypted) if llm_cfg.secret_encrypted else None
    spec = llm.LlmSpec(endpoint=llm_cfg.endpoint, model=llm_cfg.model, secret=secret)
    final = await report_skill_agent.ainvoke(
        {
            "skill_type": req.skill_type,
            "code": req.report_type_code,
            "name": req.report_type_name,
            "description": req.report_type_description,
            "llm": spec,
        }
    )
    return final["content"]
