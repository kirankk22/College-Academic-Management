from fastapi import APIRouter

from app.api import academic_catalog
from app.api import academic_history
from app.api import academic_periods
from app.api import attendance
from app.api import attendance_students
from app.api import faculty
from app.api import institutions
from app.api import students
from app.api.auth import router as auth_router
from app.api.health import router as health_router


api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(institutions.router)
api_router.include_router(students.router)
api_router.include_router(academic_history.router)
api_router.include_router(academic_periods.router)
api_router.include_router(faculty.router)
api_router.include_router(attendance_students.router)
api_router.include_router(attendance.router)
api_router.include_router(academic_catalog.router)