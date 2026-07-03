from fastapi import APIRouter

from app.api.v1 import auth, data, files, health, jobs

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(files.router)
api_router.include_router(data.router)
api_router.include_router(jobs.router)
