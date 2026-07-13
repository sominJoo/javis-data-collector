from app.schemas.base import CamelModel


class LoginRequest(CamelModel):
    # FE는 {api_key} 또는 {apiKey} 로 보낼 수 있다 (populate_by_name).
    api_key: str


class AdminLoginRequest(CamelModel):
    id: str
    password: str
