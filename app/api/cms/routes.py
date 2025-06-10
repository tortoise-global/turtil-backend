from fastapi import APIRouter

# Import all sub-routers with transformed paths
from app.api.cms.auth.routes import router as auth_router
from app.api.cms.college_placements.routes import router as college_placements_router
from app.api.cms.college_students.routes import router as college_students_router
from app.api.cms.image_upload.routes import router as image_upload_router

router = APIRouter()

# Include all routers with transformed paths: cms-[module] -> cms/[module]
router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(college_placements_router, prefix="/college-placements", tags=["College Placements"])
router.include_router(college_students_router, prefix="/college-students", tags=["College Students"])
router.include_router(image_upload_router, prefix="/image-upload", tags=["Image Upload"])