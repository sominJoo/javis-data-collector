"""로컬/개발용 시드.

- 관리자 계정 1개 생성
- (옵션) 테스트용 API Key 1개 생성 + 로컬 사용자 DB 연결 등록

실행: `python -m scripts.seed`
"""
import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core import crypto
from app.core.database import AsyncSessionLocal
from app.core.security import (
    generate_api_key,
    hash_api_key,
    hash_password,
    mask_api_key,
)
from app.models.collector import (
    ApiKeyDbConnection,
    ApiKeyEmbeddingConfig,
    ApiKeyLlmConfig,
    AdminAccount,
    CollectorApiKey,
)

ADMIN_ID = "admin"
ADMIN_PW = "admin1234"
TEST_KEY_NAME = "로컬 테스트 키"


async def main() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(AdminAccount).where(AdminAccount.login_id == ADMIN_ID))
        if admin is None:
            db.add(
                AdminAccount(
                    login_id=ADMIN_ID,
                    password_hash=hash_password(ADMIN_PW),
                    display_name="관리자",
                )
            )
            await db.commit()
            print(f"[seed] admin 계정 생성: id={ADMIN_ID} pw={ADMIN_PW}")
        else:
            print(f"[seed] admin 계정 이미 존재: id={ADMIN_ID}")

        existing_key = await db.scalar(
            select(CollectorApiKey).where(CollectorApiKey.name == TEST_KEY_NAME)
        )
        if existing_key is None:
            plain = generate_api_key()
            key = CollectorApiKey(
                name=TEST_KEY_NAME,
                api_key_hash=hash_api_key(plain),
                api_key_masked=mask_api_key(plain),
            )
            key.llm = ApiKeyLlmConfig(
                provider=settings.llm_default_provider,
                endpoint=settings.llm_default_endpoint,
                model=settings.llm_default_model,
            )
            key.embedding = ApiKeyEmbeddingConfig(
                provider=settings.llm_default_provider,
                endpoint=settings.llm_default_endpoint,
                model="text-embedding-3-small",
            )
            # 로컬 docker Postgres를 사용자 DB로도 사용 (같은 인스턴스)
            key.db_connections.append(
                ApiKeyDbConnection(
                    name="로컬 사용자 DB",
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    database=settings.postgres_database,
                    username=settings.postgres_username,
                    password_encrypted=crypto.encrypt(settings.postgres_password),
                    is_default=True,
                )
            )
            db.add(key)
            await db.commit()
            print(f"[seed] 테스트 API Key 발급(평문, 1회 노출): {plain}")
        else:
            print(f"[seed] 테스트 API Key 이미 존재: {TEST_KEY_NAME}")


if __name__ == "__main__":
    asyncio.run(main())
