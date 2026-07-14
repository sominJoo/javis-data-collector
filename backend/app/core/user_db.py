"""사용자 DB(각 API Key의 기본 연결) 접속 관리.

원본 데이터·청크·임베딩은 collector 자체 DB가 아니라, 로그인한 API Key의
기본 `api_key_db_connection`이 가리키는 외부 Postgres(사용자 DB)에 저장된다.
연결 파라미터별로 async engine을 캐시해 재사용한다.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True)
class UserDbParams:
    host: str
    port: int
    database: str
    username: str
    password: str

    def url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    def cache_key(self) -> str:
        return f"{self.username}@{self.host}:{self.port}/{self.database}"


_engines: dict[str, AsyncEngine] = {}
_makers: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_user_engine(params: UserDbParams) -> AsyncEngine:
    key = params.cache_key()
    engine = _engines.get(key)
    if engine is None:
        engine = create_async_engine(
            params.url(),
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
        _engines[key] = engine
        _makers[key] = async_sessionmaker(bind=engine, expire_on_commit=False)
    return engine


@asynccontextmanager
async def user_session(params: UserDbParams) -> AsyncGenerator[AsyncSession, None]:
    """사용자 DB용 AsyncSession 컨텍스트."""
    get_user_engine(params)
    maker = _makers[params.cache_key()]
    async with maker() as session:
        yield session


async def dispose_all() -> None:
    """캐시된 모든 사용자 DB engine 정리 (앱 종료/테스트 tear-down)."""
    for engine in _engines.values():
        await engine.dispose()
    _engines.clear()
    _makers.clear()
