from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    postgres_host: str
    postgres_port: int = 5432
    postgres_database: str
    postgres_username: str
    postgres_password: str

    file_storage_path: str = "./storage/uploads"

    jwt_secret: str
    jwt_expire_minutes: int = 60

    llm_default_provider: str = "openai"
    llm_default_endpoint: str
    llm_default_model: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
