from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.animals import router as animals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.disease_reports import router as disease_reports_router
from app.api.v1.outbreaks import router as outbreaks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(alerts_router)
api_router.include_router(dashboard_router)
api_router.include_router(animals_router)
api_router.include_router(disease_reports_router)
api_router.include_router(decisions_router)
api_router.include_router(outbreaks_router)
