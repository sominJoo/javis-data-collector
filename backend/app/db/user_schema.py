"""사용자 DB 스키마 마이그레이션 & 존재 검사.

migrate 엔드포인트가 대상 사용자 DB에 스키마/확장/테이블을 생성하고,
test 엔드포인트가 필수 테이블 존재 여부로 마이그레이션 필요 여부를 판정한다.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user_data import DATA_COLLECTOR, JARVIS, UserBase

REQUIRED_SCHEMAS = (DATA_COLLECTOR, JARVIS)
# 존재 여부 판정에 쓰는 대표 테이블
_PROBE_TABLE = f"{DATA_COLLECTOR}.report_type"

# jarvis.file_classification_type 기본 시드 (code, name, description, sort_order)
DEFAULT_CLASSIFICATION_TYPES = (
    ("RFP", "제안요청서", "제안요청서 문서", 1),
    ("PROPOSAL", "제안서", "제안서 문서", 2),
    ("TOC", "목차", "목차 정보 또는 목차 문서", 3),
    ("SECTION_GUIDE", "섹션 작성 가이드", "섹션별 작성 방향 정보", 4),
    ("CONCEPT", "핵심개념", "핵심개념, 기술개념, 용어 정보", 5),
    ("REQUIREMENT", "요구사항", "요구사항 목록 또는 요구사항 포함 문서", 6),
    ("EVALUATION_CRITERIA", "평가 기준", "평가 항목, 배점, 평가 기준 정보", 7),
    ("REFERENCE", "참고자료", "작성 근거로 사용할 참고자료", 8),
    ("REPORT", "보고서", "일반 보고서", 9),
    ("MANUAL", "매뉴얼", "매뉴얼 또는 가이드 문서", 10),
    ("UNKNOWN", "미분류", "분류되지 않은 문서", 99),
)


async def needs_migration(engine: AsyncEngine) -> bool:
    """필수 스키마·테이블이 없으면 True(마이그레이션 필요)."""
    async with engine.connect() as conn:
        reg = await conn.scalar(text(f"SELECT to_regclass('{_PROBE_TABLE}')"))
    return reg is None


async def apply_migration(engine: AsyncEngine) -> None:
    """대상 사용자 DB에 확장·스키마·테이블 생성 + file_classification_type 시드."""
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        for schema in REQUIRED_SCHEMAS:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await conn.run_sync(UserBase.metadata.create_all)

        count = await conn.scalar(
            text(f"SELECT count(*) FROM {JARVIS}.file_classification_type")
        )
        if not count:
            for code, name, description, sort_order in DEFAULT_CLASSIFICATION_TYPES:
                await conn.execute(
                    text(
                        f"INSERT INTO {JARVIS}.file_classification_type "
                        "(code, name, description, sort_order) "
                        "VALUES (:code, :name, :description, :sort_order)"
                    ),
                    {
                        "code": code,
                        "name": name,
                        "description": description,
                        "sort_order": sort_order,
                    },
                )
