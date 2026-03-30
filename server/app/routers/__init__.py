"""API routers package."""

from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.parse import router as parse_router
from app.routers.rag import router as rag_router
from app.routers.schedules import router as schedules_router
from app.routers.share import router as share_router
from app.routers.sync import router as sync_router

__all__ = ["auth_router", "health_router", "schedules_router", "sync_router", "parse_router", "rag_router", "share_router"]

