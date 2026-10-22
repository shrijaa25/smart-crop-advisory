from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CropCycle, CropStageRule


def get_crop_stage(db: Session, crop_cycle_id: int, target_date: date) -> dict:
    cycle = db.get(CropCycle, crop_cycle_id)
    if cycle is None:
        raise ValueError("Crop cycle not found.")

    crop_age = (target_date - cycle.planting_date).days
    result = {
        "crop_cycle_id": cycle.id,
        "crop_name": cycle.crop_name,
        "target_date": target_date,
        "crop_age_days": crop_age,
        "stage_name": None,
        "stage_rule_id": None,
        "message": None,
    }
    if crop_age < 0:
        result["message"] = "The target date is before transplanting."
        return result

    matches = db.scalars(
        select(CropStageRule).where(
            CropStageRule.crop_name == cycle.crop_name,
            CropStageRule.verification_status == "verified",
            CropStageRule.days_basis == "after_transplanting",
            CropStageRule.day_start.is_not(None),
            CropStageRule.day_end.is_not(None),
            CropStageRule.day_start <= crop_age,
            CropStageRule.day_end >= crop_age,
        )
    ).all()

    if len(matches) == 1:
        result["stage_name"] = matches[0].stage_name
        result["stage_rule_id"] = matches[0].id
        result["message"] = "Stage identified from a verified crop-stage rule."
    elif not matches:
        result["message"] = "No verified crop-stage rule matches this crop age."
    else:
        result["message"] = "Multiple verified crop-stage rules match; stage is unavailable."
    return result
