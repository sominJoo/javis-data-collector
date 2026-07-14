"""로깅 설정. stdlib logging과 structlog를 하나의 파이프라인으로 통합한다.

- 앱/외부 라이브러리의 `logging.getLogger(...)` 로그와 `get_logger()`(structlog) 로그가
  동일한 핸들러·동일한 포맷으로 출력된다.
- 콘솔(TTY)에서는 사람이 읽기 쉬운 ConsoleRenderer, 그 외(컨테이너/파일 리다이렉트)에서는
  JSONRenderer로 자동 전환한다.
- configure_logging은 멱등하다: alembic env.py의 fileConfig가 root 로거를 덮어써도
  다시 호출해 복구할 수 있도록 root 핸들러를 명시적으로 초기화 후 재설정한다.
"""
import logging
import sys

import structlog


def _resolve_level(level: int | str | None) -> int:
    """레벨 인자(int/문자열/None)를 로깅 레벨 정수로 변환한다.

    None이면 settings.log_level을 읽는다. 잘못된 값은 INFO로 폴백.
    """
    if level is None:
        # 순환 import 방지를 위해 지연 import.
        from app.core.config import get_settings

        level = get_settings().log_level
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def configure_logging(level: int | str | None = None) -> None:
    resolved = _resolve_level(level)

    # structlog·stdlib 로그에 공통으로 적용할 전처리기.
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # 최종 렌더러: TTY면 사람이 읽기 쉬운 콘솔, 아니면 JSON.
    if sys.stdout.isatty():
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        # ensure_ascii=False: 한글이 \uXXXX로 이스케이프되지 않고 그대로 출력.
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)

    # structlog: 마지막에 stdlib logging으로 넘겨 단일 핸들러에서 렌더링.
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(resolved),
        cache_logger_on_first_use=True,
    )

    # stdlib 핸들러: structlog·순수 stdlib 로그를 동일 포맷으로 렌더링.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,  # structlog을 안 거친 로그(외부 라이브러리)용
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(resolved)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
