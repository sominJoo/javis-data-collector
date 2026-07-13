class NotFoundError(Exception):
    """리소스를 찾을 수 없음 → ApiResponse.failure 로 변환."""


class ConflictError(Exception):
    """유일성 위반 등 충돌 → ApiResponse.failure 로 변환."""
