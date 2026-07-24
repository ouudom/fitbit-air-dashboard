from fastapi import APIRouter

from src.modules.agent_access.router import router as mcp_token_router
from src.modules.auth.router import router as auth_router
from src.modules.dashboard.router import router as dashboard_router
from src.modules.google_health.router import router as google_health_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(mcp_token_router)
api_router.include_router(google_health_router)
api_router.include_router(dashboard_router)
