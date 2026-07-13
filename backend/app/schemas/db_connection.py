from app.schemas.base import CamelModel


class DbConnectionTestRequest(CamelModel):
    name: str = ""
    host: str
    port: int = 5432
    database: str
    username: str
    password: str = ""


class DbTestResultOut(CamelModel):
    ok: bool
    needs_migration: bool
