from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.links import router as links_router
from app.api.v1.routes.stats import router as stats_router
from app.api.v1.routes.redirect import router as redirect_router

# Aggregate all v1 routes — order matters: specific routes before wildcard /{short_id}
router = APIRouter()
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(links_router)
router.include_router(stats_router)
router.include_router(redirect_router)  # must be last — wildcard /{short_id}
