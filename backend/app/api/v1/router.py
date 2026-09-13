from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.animals import router as animals_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.clinical import router as clinical_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.disease_reports import router as disease_reports_router
from app.api.v1.farms import router as farms_router
from app.api.v1.laboratory import router as laboratory_router
from app.api.v1.outbreaks import router as outbreaks_router
from app.api.v1.reference_data import router as references_router
from app.api.v1.report_drafts import router as drafts_router
from app.api.v1.rule_packs import router as rules_router

api_router = APIRouter()
api_router.include_router(rules_router)
api_router.include_router(drafts_router)
api_router.include_router(references_router)
api_router.include_router(cases_router)
api_router.include_router(clinical_router)
api_router.include_router(laboratory_router)
api_router.include_router(farms_router)
api_router.include_router(auth_router)
api_router.include_router(alerts_router)
api_router.include_router(dashboard_router)
api_router.include_router(animals_router)
api_router.include_router(disease_reports_router)
api_router.include_router(decisions_router)
api_router.include_router(outbreaks_router)
