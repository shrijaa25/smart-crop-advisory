from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_farmer
from app.db.session import get_db
from app.models import CropCycle, DailyTask, Farm, Farmer, FarmerObservation, TaskHistory, WeatherRecord
from app.schemas.tasks import DailyTaskOut, GenerateTasksResponse
from app.services.crop_stage import get_crop_stage
from app.services.weather import get_weather_for_farm
from app.services.task_engine import (
    generate_daily_monitoring_tasks,
    generate_daily_tasks,
    generate_fertilizer_review_alerts,
    generate_irrigation_tasks,
    generate_one_time_fertilizer_tasks,
    generate_stage_milestone_tasks,
    generate_fallback_irrigation_tasks,
)
from app.services.excel_task_schedule import get_safe_monitoring_task_details
from app.services.weather_knowledge import (
    get_weather_advisory_candidates,
    normalise_weather_for_advisory,
    _pesticide_disease_details,
)
router = APIRouter(prefix="/tasks", tags=["Daily Tasks"])


async def _generate_weather_risk_inspection_tasks(
    db: Session,
    farmer_id: int,
    target_date: date,
) -> int:
    """Save deduplicated, weather-based inspection tasks for active crops."""
    cycles = db.scalars(
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            Farm.farmer_id == farmer_id,
            CropCycle.status == "active",
            CropCycle.planting_date <= target_date,
        )
    ).all()

    inserted = 0

    try:
        for cycle in cycles:
            farm = db.get(Farm, cycle.farm_id)
            if farm is None:
                continue

            weather = await get_weather_for_farm(
                village=farm.village,
                district=farm.district,
                state=farm.state,
                latitude=farm.latitude,
                longitude=farm.longitude,
                target_date=target_date,
            )

            advisory_weather = normalise_weather_for_advisory(
                weather,
                target_date.isoformat(),
            )

            advisories = get_weather_advisory_candidates(
                cycle.crop_name,
                advisory_weather,
            )

            if advisories.get("status") != "ok":
                continue

            for risk in advisories.get("risk_candidates", []):
                risk_name = str(risk.get("risk") or "").strip()
                if not risk_name:
                    continue

                title = f"Inspect weather risk: {risk_name}"

                existing = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.source_rule_type == "weather_risk",
                        DailyTask.title == title,
                    )
                )

                if existing is not None:
                    continue

                details = [
                    "Potential weather-related risk; this is not a confirmed diagnosis.",
                    f"Weather match status: {risk.get('match_status', 'matched')}",
                    f"Marathi disease name (workbook): {risk.get('marathi_name', 'Not available')}",
                    f"Chemical combination transcribed from workbook (NOT VERIFIED): {risk.get('chemical_combination', 'Not available')}",
                    f"Brand name transcribed from workbook (NOT VERIFIED): {risk.get('brand_name', 'Not available')}",
                    f"Treatment review status: {risk.get('treatment_review_status', 'unavailable')}",
                    f"Treatment safety note: {risk.get('treatment_safety_note', 'No verified treatment recommendation available.')}",
                    f"Weather profile: {risk.get('weather_profile', 'Not specified')}",
                    "Conditions requiring field verification: "
                    f"{', '.join(risk.get('missing_conditions', [])) or 'None'}",
                    f"Symptoms to inspect: {risk.get('symptoms_to_check', 'Inspect the crop for unusual symptoms.')}",
                    f"Suggested prevention: {risk.get('prevention', 'Inspect the crop and record observations.')}",
                    "Record field observations and seek verified local agricultural guidance if symptoms are found.",
                    "No automatic pesticide recommendation is made.",
                ]

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description=" ".join(details),
                        status="pending",
                        source_rule_type="weather_risk",
                        source_rule_id=None,
                        weather_context={
                            "status": advisory_weather["status"],
                            "target_date": target_date.isoformat(),
                            "source": weather.get("source"),
                            "temperature_c": advisory_weather["temperature_c"],
                            "humidity_percent": advisory_weather["relative_humidity"],
                            "rainfall_mm": advisory_weather["precipitation_mm"],
                            "risk": risk_name,
                            "review_status": risk.get("review_status", "needs_review"),
                        },
                    )
                )
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


class TaskStatusUpdate(BaseModel):
    status: str
    notes: str | None = None
    new_due_date: date | None = None


class DiseaseTreatmentRequest(BaseModel):
    crop: str
    disease: str


@router.get("/disease-detection/status")
def disease_detection_status():
    """Report model availability without making or fabricating a prediction."""
    return {
        "available": False,
        "model_version": None,
        "reason": "No trained CNN model artifact or inference service is installed.",
        "prediction_policy": "Predictions are decision support; low confidence requires inspection and cannot trigger pesticide treatment.",
    }



@router.get("/weather-risk/{crop_cycle_id}")
async def crop_weather_risk(
    crop_cycle_id: int,
    target_date: date = Query(default_factory=date.today),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Return date-specific weather screening risks for an owned crop cycle."""
    cycle = db.scalar(
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            CropCycle.id == crop_cycle_id,
            Farm.farmer_id == farmer.id,
        )
    )

    if cycle is None:
        raise HTTPException(
            status_code=404,
            detail="Crop cycle not found.",
        )

    farm = db.get(Farm, cycle.farm_id)

    if farm is None:
        raise HTTPException(
            status_code=404,
            detail="Farm not found.",
        )

    weather = await get_weather_for_farm(
        village=farm.village,
        district=farm.district,
        state=farm.state,
        latitude=farm.latitude,
        longitude=farm.longitude,
        target_date=target_date,
    )

    # Use today's same-day current temperature, or the selected date's daily
    # maximum for another date. Humidity and moisture do not gate alerts.
    advisory_weather = normalise_weather_for_advisory(
        weather,
        target_date.isoformat(),
    )

    advisories = get_weather_advisory_candidates(
        cycle.crop_name,
        advisory_weather,
    )

    return {
        "crop_cycle_id": cycle.id,
        "crop_name": cycle.crop_name,
        "target_date": target_date.isoformat(),
        "weather": weather,
        "advisories": advisories,
        "disclaimer": (
            "These are preliminary weather-based risk candidates, "
            "not confirmed disease diagnoses. Inspect the crop and "
            "seek verified local agricultural guidance before treatment. "
            "No automatic chemical recommendation is made."
        ),
    }


@router.post("/disease-treatment")
def disease_treatment_lookup(
    payload: DiseaseTreatmentRequest,
    farmer: Farmer = Depends(get_current_farmer),
):
    """Look up a workbook treatment only after the farmer reports symptoms."""
    crop = payload.crop.strip().casefold()
    disease = payload.disease.strip()

    if crop not in {"tomato", "chilli"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported crop. Use tomato or chilli.",
        )
    if not disease:
        raise HTTPException(
            status_code=400,
            detail="A disease name is required.",
        )

    details = _pesticide_disease_details(crop, disease)
    if details.get("review_status") == "unavailable":
        raise HTTPException(
            status_code=404,
            detail=details.get(
                "message",
                "No matching treatment record found in the workbook.",
            ),
        )
    return details


@router.get("/excel-schedule/{crop_cycle_id}")
def get_crop_excel_schedule(
    crop_cycle_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Return the safe Excel monitoring rule for this crop's current DAT."""
    cycle = db.scalar(
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            CropCycle.id == crop_cycle_id,
            Farm.farmer_id == farmer.id,
        )
    )

    if cycle is None:
        raise HTTPException(
            status_code=404,
            detail="Crop cycle not found.",
        )

    dat = (date.today() - cycle.planting_date).days

    if dat < 1:
        return {
            "crop_cycle_id": cycle.id,
            "crop_name": cycle.crop_name,
            "dat": dat,
            "schedule_available": False,
            "message": (
                "The Excel monitoring schedule starts on Day 1 "
                "after the planting/transplanting date."
            ),
            "task": None,
        }

    task = get_safe_monitoring_task_details(cycle.crop_name, dat)

    return {
        "crop_cycle_id": cycle.id,
        "crop_name": cycle.crop_name,
        "dat": dat,
        "schedule_available": task is not None,
        "task": task,
        "message": (
            "Safe monitoring rule found."
            if task is not None
            else "No approved Excel monitoring rule exists for this DAT."
        ),
    }


class ObservationCreate(BaseModel):
    crop_cycle_id: int = Field(ge=1)
    task_id: int | None = Field(default=None, ge=1)
    note: str = Field(min_length=1, max_length=5000)
    photo_reference: str | None = Field(default=None, max_length=500)


@router.get("", response_model=list[DailyTaskOut])
def list_tasks(
    task_date: date | None = Query(default=None),
    crop_cycle_id: int | None = Query(default=None, ge=1),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    statement = (
        select(DailyTask)
        .join(CropCycle, DailyTask.crop_cycle_id == CropCycle.id)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(Farm.farmer_id == farmer.id)
    )
    if task_date is not None:
        statement = statement.where(DailyTask.task_date == task_date)
    if crop_cycle_id is not None:
        statement = statement.where(DailyTask.crop_cycle_id == crop_cycle_id)
    return db.scalars(statement.order_by(DailyTask.task_date, DailyTask.id)).all()


@router.get("/upcoming", response_model=list[DailyTaskOut])
def upcoming_tasks(
    from_date: date = Query(default_factory=date.today),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(DailyTask).join(CropCycle).join(Farm)
        .where(Farm.farmer_id == farmer.id, DailyTask.task_date >= from_date)
        .order_by(DailyTask.task_date, DailyTask.id)
    ).all()


@router.get("/observations")
def list_observations(
    crop_cycle_id: int | None = Query(default=None, ge=1),
    farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db),
):
    statement = select(FarmerObservation).join(CropCycle).join(Farm).where(Farm.farmer_id == farmer.id)
    if crop_cycle_id is not None:
        statement = statement.where(FarmerObservation.crop_cycle_id == crop_cycle_id)
    return db.scalars(statement.order_by(FarmerObservation.created_at.desc())).all()


@router.post("/observations", status_code=http_status.HTTP_201_CREATED)
def create_observation(
    payload: ObservationCreate,
    farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db),
):
    cycle = db.scalar(select(CropCycle).join(Farm).where(
        CropCycle.id == payload.crop_cycle_id, Farm.farmer_id == farmer.id
    ))
    if cycle is None:
        raise HTTPException(status_code=404, detail="Crop cycle not found.")
    if payload.task_id is not None:
        task = _owned_task(db, payload.task_id, farmer.id)
        if task.crop_cycle_id != cycle.id:
            raise HTTPException(status_code=400, detail="Task does not belong to this crop cycle.")
    observation = FarmerObservation(**payload.model_dump())
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@router.post("/generate", response_model=GenerateTasksResponse)
async def generate_tasks(
    target_date: date = Query(default_factory=date.today),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    try:
        monitoring_count = generate_daily_monitoring_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        fertilizer_count = generate_daily_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        fertilizer_review_count = generate_fertilizer_review_alerts(
            db, target_date=target_date, farmer_id=farmer.id
        )
        onetime_count = generate_one_time_fertilizer_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        irrigation_count = generate_irrigation_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        irrigation_check_count = generate_fallback_irrigation_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        milestone_count = generate_stage_milestone_tasks(
            db, target_date=target_date, farmer_id=farmer.id
        )
        weather_risk_count = await _generate_weather_risk_inspection_tasks(
            db,
            farmer_id=farmer.id,
            target_date=target_date,
        )
    except Exception as exc:
        import logging

        logging.exception("Daily task generation failed")
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate daily tasks: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    total = (
        monitoring_count
        + fertilizer_count
        + fertilizer_review_count
        + onetime_count
        + irrigation_count
        + irrigation_check_count
        + milestone_count
        + weather_risk_count
    )
    return GenerateTasksResponse(
        target_date=target_date,
        tasks_created=total,
        fertilizer_review_alerts_created=fertilizer_review_count,
        message=(
            "Task generation completed. "
            f"Daily crop monitoring: {monitoring_count}; "
            f"Fertilizer reminders: {fertilizer_count + onetime_count}; "
            f"Fertilizer schedule review alerts: {fertilizer_review_count}; "
            f"irrigation reminders: {irrigation_count + irrigation_check_count}; "
            f"stage milestones: {milestone_count}; "
            f"Weather-risk inspection tasks: {weather_risk_count}."
        ),
    )


@router.get("/crop-stage")
def crop_stage(
    crop_cycle_id: int = Query(..., ge=1),
    target_date: date = Query(default_factory=date.today),
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    owned_cycle_id = db.scalar(
        select(CropCycle.id)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            CropCycle.id == crop_cycle_id,
            Farm.farmer_id == farmer.id,
        )
    )
    if owned_cycle_id is None:
        raise HTTPException(status_code=404, detail="Crop cycle not found.")
    try:
        return get_crop_stage(db, owned_cycle_id, target_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Crop cycle not found.") from exc


def _owned_task(db: Session, task_id: int, farmer_id: int) -> DailyTask:
    """Return the task only if it belongs to this farmer's crop cycle."""
    task = db.scalar(
        select(DailyTask)
        .join(CropCycle, DailyTask.crop_cycle_id == CropCycle.id)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(DailyTask.id == task_id, Farm.farmer_id == farmer_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@router.patch("/{task_id}/complete", response_model=DailyTaskOut)
def complete_task(
    task_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Mark a task as completed."""
    task = _owned_task(db, task_id, farmer.id)
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.add(TaskHistory(task_id=task.id, action="completed"))
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/reopen", response_model=DailyTaskOut)
def reopen_task(
    task_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Reopen a completed task back to pending."""
    task = _owned_task(db, task_id, farmer.id)
    task.status = "pending"
    task.completed_at = None
    db.add(TaskHistory(task_id=task.id, action="reopened"))
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=DailyTaskOut)
def update_task_status(
    task_id: int, payload: TaskStatusUpdate,
    farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db),
):
    allowed = {"pending", "completed", "skipped", "rescheduled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=422, detail=f"Status must be one of: {', '.join(sorted(allowed))}.")
    if payload.status == "rescheduled" and payload.new_due_date is None:
        raise HTTPException(status_code=422, detail="new_due_date is required when rescheduling.")
    task = _owned_task(db, task_id, farmer.id)
    task.status = payload.status
    if payload.new_due_date is not None:
        task.task_date = payload.new_due_date
    task.completed_at = datetime.utcnow() if payload.status == "completed" else None
    history_notes = payload.notes
    if payload.new_due_date is not None:
        history_notes = f"{history_notes or ''} Rescheduled to {payload.new_due_date.isoformat()}.".strip()
    db.add(TaskHistory(task_id=task.id, action=payload.status, notes=history_notes))
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}/history")
def task_history(
    task_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    _owned_task(db, task_id, farmer.id)
    return db.scalars(
        select(TaskHistory).where(TaskHistory.task_id == task_id).order_by(TaskHistory.created_at, TaskHistory.id)
    ).all()
