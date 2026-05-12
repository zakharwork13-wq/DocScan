from fastapi import APIRouter

from .endpoints.audit import router as audit_router
from .endpoints.auth import router as auth_router
from .endpoints.rules import router as rules_router
from .endpoints.scans import router as scans_router
from .endpoints.stats import router as stats_router
from .endpoints.users import router as users_router
from .endpoints.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(scans_router, prefix="/scans", tags=["scans"])
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(rules_router, prefix="/rules", tags=["rules"])
api_router.include_router(ws_router, tags=["websocket"])
