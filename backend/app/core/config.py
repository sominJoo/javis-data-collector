from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend 디렉토리(= app/core/config.py의 3단계 상위). 상대 저장경로 앵커 기준.
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"), env_file_encoding="utf-8"
    )

    postgres_host: str
    postgres_port: int = 5432
    postgres_database: str
    postgres_username: str
    postgres_password: str

    file_storage_path: str = "./storage/uploads"

    jwt_secret: str
    jwt_expire_minutes: int = 60

    # API Key/DB 비밀번호/LLM secret 등을 대칭 암호화하는 Fernet 키 (base64 32바이트).
    encryption_key: str

    llm_default_provider: str = "openai"
    llm_default_endpoint: str
    llm_default_model: str

    # 전역 OpenAI 자격/임베딩 모델. API Key별 secret이 없을 때의 기본값으로 사용.
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"

    # true면 외부 LLM 없이 결정적 placeholder로 파이프라인을 구동 (로컬/CI 검증용).
    llm_stub_mode: bool = False

    # LLM 요청당 허용할 최대 입력 토큰. 모델 컨텍스트 한도보다 낮게 잡아 출력·오차 여유를 둔다.
    # map-reduce 요약의 세그먼트 크기와 전체 원문 프롬프트(보고자/TOC/STYLE/키워드) 클리핑 기준.
    # 토큰은 cl100k_base로 측정(한글 과대 추정 → 실제 한도 대비 보수적). 모델 한도 32768 기준 여유 확보.
    llm_max_input_tokens: int = 28000

    # 로그 레벨 (DEBUG/INFO/WARNING/ERROR). 로컬 디버깅 시 DEBUG로 낮춘다.
    log_level: str = "INFO"

    # true면 앱 startup에서 운영 DB(collector_service) Alembic 마이그레이션을 자동 실행.
    # 테스트/특수 배포에서 끄고 싶으면 false.
    auto_migrate: bool = True

    # 초기 관리자 계정. 마이그레이션(0003) 시 이 계정이 없으면 생성한다.
    # 둘 다 비어 있으면 admin 생성을 건너뛴다(운영에서 의도치 않은 기본 계정 방지).
    initial_admin_id: str | None = None
    initial_admin_password: str | None = None

    @property
    def storage_root(self) -> Path:
        """업로드 저장 루트를 cwd와 무관한 절대경로로 해석한다.

        file_storage_path가 상대경로면 backend 디렉토리를 기준으로 앵커링한다.
        (상대경로를 그대로 쓰면 앱 실행 cwd에 따라 파일을 못 찾아 파싱이 실패한다.)
        """
        p = Path(self.file_storage_path)
        if not p.is_absolute():
            p = _BACKEND_DIR / p
        return p.resolve()

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
