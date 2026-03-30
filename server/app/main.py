from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.parse import router as parse_router
from app.routers.rag import router as rag_router
from app.routers.schedules import router as schedules_router
from app.routers.share import router as share_router
from app.routers.sync import router as sync_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(parse_router, prefix=settings.api_prefix)
app.include_router(rag_router, prefix=settings.api_prefix)
app.include_router(schedules_router, prefix=settings.api_prefix)
app.include_router(share_router, prefix=settings.api_prefix)
app.include_router(sync_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
async def read_root() -> dict[str, str]:
    return {
        "message": "Smart Schedule backend skeleton is ready.",
        "docs": "/docs",
    }

