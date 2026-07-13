from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.migrations import upgrade_to_head
from app.schemas.common import ApiResponse

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 운영 DB(collector_service) 스키마를 항상 최신으로 맞춘 뒤 서비스 기동.
    if get_settings().auto_migrate:
        await upgrade_to_head()
    yield


app = FastAPI(title="jarivs-data-collector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.failure(str(exc.detail)).model_dump(),
    )


app.include_router(api_router, prefix="/api/v1")
