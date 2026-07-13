from app.schemas.base import CamelModel


class SessionOut(CamelModel):
    token: str
    role: str  # "user" | "admin"
    display_name: str
