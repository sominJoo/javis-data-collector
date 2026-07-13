from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().encryption_key.encode())


def encrypt(plain: str) -> str:
    """평문을 Fernet 토큰(문자열)으로 암호화."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    """Fernet 토큰을 평문으로 복호화."""
    return _fernet().decrypt(token.encode()).decode()


def generate_key() -> str:
    """새 Fernet 키 생성 (초기 설정/시드 편의용)."""
    return Fernet.generate_key().decode()
