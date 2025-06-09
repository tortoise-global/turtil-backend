from fastapi import APIRouter

# Import all sub-routers with transformed paths
from app.api.cms.auth.routes import router as auth_router
from app.api.cms.college-degree.routes import router as college_degree_router
from app.api.cms.college-placements.routes import router as college_placements_router
from app.api.cms.college-students.routes import router as college_students_router
from app.api.cms.image-upload.routes import router as image_upload_router

router = APIRouter()

# Include all routers with transformed paths: cms-[module] -> cms/[module]
router.include_router(auth_router, prefix="/auth", tags=["cms-auth"])
router.include_router(college_degree_router, prefix="/college-degree", tags=["cms-college-degree"])
router.include_router(college_placements_router, prefix="/college-placements", tags=["cms-college-placements"])
router.include_router(college_students_router, prefix="/college-students", tags=["cms-college-students"])
router.include_router(image_upload_router, prefix="/image-upload", tags=["cms-image-upload"])