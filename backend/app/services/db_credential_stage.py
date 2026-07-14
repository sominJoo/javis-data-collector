"""DB 연결 비밀번호 임시 보관소.

프론트는 연결 테스트/마이그레이션 때만 비밀번호를 보내고, API Key 저장 payload의
dbConnections에는 비밀번호를 포함하지 않는다(타입에 password 없음). 이 간극을 메우기 위해
test/migrate 성공 시 비밀번호를 (암호화하여) 연결 식별자별로 잠시 보관했다가,
saveApiKey가 영속 저장(api_key_db_connection.password_encrypted)할 때 꺼내 쓴다.

durable 저장은 DB이며, 이 스테이지는 test→save 사이(초 단위)만 다리 역할을 한다.
"""
from app.core import crypto


def _key(host: str, port: int, database: str, username: str) -> str:
    return f"{username}@{host}:{port}/{database}"


_stage: dict[str, str] = {}


def stage(host: str, port: int, database: str, username: str, password: str) -> None:
    _stage[_key(host, port, database, username)] = crypto.encrypt(password) if password else ""


def take(host: str, port: int, database: str, username: str) -> str | None:
    """암호화된 비밀번호(또는 빈 문자열)를 반환하고 스테이지에서 제거. 없으면 None."""
    return _stage.pop(_key(host, port, database, username), None)
