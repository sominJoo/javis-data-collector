from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """모든 요청/응답 스키마의 공통 베이스.

    - 응답은 camelCase(alias)로 직렬화 → 프론트엔드 타입과 일치.
    - 요청은 camelCase/snake_case 둘 다 수용(populate_by_name).
    - ORM 객체를 그대로 직렬화 가능(from_attributes).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
