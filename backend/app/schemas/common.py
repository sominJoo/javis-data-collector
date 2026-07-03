from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """설계 문서 7장 API 공통 응답 포맷."""

    result: int = 1
    errorMessage: str = ""
    data: DataT | None = None

    @classmethod
    def success(cls, data: DataT | None = None) -> "ApiResponse[DataT]":
        return cls(result=1, errorMessage="", data=data)

    @classmethod
    def failure(cls, error_message: str) -> "ApiResponse[DataT]":
        return cls(result=0, errorMessage=error_message, data=None)
