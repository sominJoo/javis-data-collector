from enum import StrEnum

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Schema(StrEnum):
    """설계 문서 1.3 Database 항목에 정의된 3개 스키마."""

    COLLECTOR_SERVICE = "collector_service"
    JARVIS = "jarvis"
    DATA_COLLECTOR = "data_collector"


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """공통 선언적 Base. 실제 테이블 모델은 `__table_args__ = {"schema": Schema.XXX}`로
    스키마를 지정해 정의한다 (예: `models/jarvis/file.py`)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
