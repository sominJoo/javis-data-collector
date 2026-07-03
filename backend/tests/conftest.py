import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DATABASE", "jarivs_data_collector_test")
os.environ.setdefault("POSTGRES_USERNAME", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("LLM_DEFAULT_ENDPOINT", "https://api.openai.com/v1")
os.environ.setdefault("LLM_DEFAULT_MODEL", "gpt-4o-mini")
