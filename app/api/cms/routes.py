from fastapi import APIRouter

from app.api.cms.academic.routes import router as academic_router

# Import all CMS routers
from app.api.cms.auth.routes import router as auth_router
from app.api.cms.hierarchy.routes import router as hierarchy_router
from app.api.cms.permissions.routes import router as permissions_router

router = APIRouter()

# Include all CMS routes
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(permissions_router, prefix="/permissions", tags=["Permissions"])
router.include_router(academic_router, prefix="/academic", tags=["Academic Structure"])
router.include_router(hierarchy_router, prefix="/hierarchy", tags=["User Hierarchy"])
