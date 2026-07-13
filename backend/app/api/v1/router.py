from fastapi import APIRouter

from app.api.v1 import admin, auth, data, files, jobs, report_types

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(report_types.router)
api_router.include_router(data.router)
api_router.include_router(files.router)
api_router.include_router(jobs.router)
