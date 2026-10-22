
"""Read-only API endpoints for Excel-based crop knowledge."""

from fastapi import APIRouter, Depends

from app.api.v1.auth import get_current_farmer
from app.models import Farmer
from app.services.excel_knowledge_service import (
    get_excel_knowledge_summary,
    get_preplant_task_records,
    get_weather_disease_risk_records,
    get_daily_schedule_records,
    get_fertilizer_schedule_records,
    get_prevention_and_pest_disease_references,
    get_cnn_data_requirements,
    get_active_safe_monitoring_records,
)

router = APIRouter(
    prefix="/knowledge/excel",
    tags=["Excel Knowledge Base"],
)


@router.get("/summary")
def excel_knowledge_summary(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return record counts for the Excel knowledge sources."""
    return get_excel_knowledge_summary()


@router.get("/preplant")
def excel_preplant_tasks(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return pre-planting records, preserving their review status."""
    return {
        "count": len(get_preplant_task_records()),
        "records": get_preplant_task_records(),
    }


@router.get("/weather-disease-risks")
def excel_weather_disease_risks(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return source weather and disease-risk records."""
    records = get_weather_disease_risk_records()
    return {"count": len(records), "records": records}


@router.get("/daily-schedule")
def excel_daily_schedule(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return all day 1–30 schedule records, including review-only rows."""
    records = get_daily_schedule_records()
    return {"count": len(records), "records": records}


@router.get("/fertilizer")
def excel_fertilizer_schedule(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return fertilizer source records without activating them."""
    return get_fertilizer_schedule_records()


@router.get("/references")
def excel_prevention_and_pest_disease_references(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return prevention, disease, pest, and review reference records."""
    return get_prevention_and_pest_disease_references()


@router.get("/cnn-requirements")
def excel_cnn_requirements(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return image-model dataset requirements."""
    records = get_cnn_data_requirements()
    return {"count": len(records), "records": records}


@router.get("/active-monitoring")
def excel_active_monitoring(
    farmer: Farmer = Depends(get_current_farmer),
):
    """Return only active safe monitoring tasks."""
    records = get_active_safe_monitoring_records()
    return {"count": len(records), "records": records}
