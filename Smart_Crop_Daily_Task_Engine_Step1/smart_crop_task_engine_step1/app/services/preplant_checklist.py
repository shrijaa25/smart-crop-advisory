"""Safe pre-planting checklist for tomato and chilli.

This module contains general preparation tasks only.
It does not prescribe fertilizer, pesticide, or disease treatments.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CropCycle, DailyTask, Farm


SUPPORTED_CROPS = {"tomato", "chilli"}


PREPLANT_CHECKLIST: list[dict[str, Any]] = [
    {
        "task_id": "SAFE-PRE-001",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 14,
        "title": "Inspect the field and drainage",
        "description": (
            "Inspect the field for waterlogging, blocked drainage, "
            "and areas where water may collect. Plan corrections "
            "before planting."
        ),
        "category": "field_preparation",
    },
    {
        "task_id": "SAFE-PRE-002",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 7,
        "title": "Check irrigation and water availability",
        "description": (
            "Confirm that a reliable water source is available "
            "and that the irrigation arrangement is working."
        ),
        "category": "water_readiness",
    },
    {
        "task_id": "SAFE-PRE-003",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 7,
        "title": "Prepare the planting area",
        "description": (
            "Remove unwanted debris and prepare the planting area "
            "according to locally recommended practices for the crop "
            "and soil conditions."
        ),
        "category": "field_preparation",
    },
    {
        "task_id": "SAFE-PRE-004",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 3,
        "title": "Inspect seedlings before transplanting",
        "description": (
            "Check seedlings for healthy growth, visible damage, "
            "or unusual symptoms. Set aside unhealthy seedlings "
            "for assessment rather than transplanting them blindly."
        ),
        "category": "seedling_readiness",
    },
    {
        "task_id": "SAFE-PRE-005",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 1,
        "title": "Clean and prepare planting tools",
        "description": (
            "Clean the tools and containers needed for planting. "
            "Check that they are in usable condition."
        ),
        "category": "tool_readiness",
    },
    {
        "task_id": "SAFE-PRE-006",
        "crop_scope": ["tomato", "chilli"],
        "days_before_planting": 1,
        "title": "Confirm planting-day readiness",
        "description": (
            "Confirm seedling availability, field readiness, water "
            "access, and the local weather forecast. Reassess timing "
            "if severe weather is expected."
        ),
        "category": "planting_readiness",
    },
]


def get_preplant_checklist(crop_name: str) -> list[dict[str, Any]]:
    """Return safe pre-planting checklist items for a supported crop."""
    normalized_crop = (crop_name or "").strip().lower()

    if normalized_crop not in SUPPORTED_CROPS:
        return []

    return [
        dict(task)
        for task in PREPLANT_CHECKLIST
        if normalized_crop in task["crop_scope"]
    ]


def get_scheduled_preplant_tasks(
    crop_name: str,
    planting_date: date,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return checklist tasks due on or before planting day.

    Tasks are returned only during their scheduled date window:
    from the task's due date through the planting date.
    """
    if reference_date is None:
        reference_date = date.today()

    if reference_date > planting_date:
        return []

    scheduled_tasks = []

    for task in get_preplant_checklist(crop_name):
        days_before = task["days_before_planting"]
        due_date = planting_date - timedelta(days=days_before)

        if due_date == reference_date:
            scheduled_task = dict(task)
            scheduled_task["due_date"] = due_date
            scheduled_tasks.append(scheduled_task)

    return scheduled_tasks


def generate_preplant_checklist_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
    crop_cycle_id: int | None = None,
) -> int:
    """Create due pre-planting checklist tasks for future crop cycles.

    This generator is separate from daily monitoring and fertilizer logic.
    It creates only general checklist tasks, never treatment instructions.
    """
    if target_date is None:
        target_date = date.today()

    statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            CropCycle.status == "active",
            CropCycle.planting_date > target_date,
        )
    )

    if farmer_id is not None:
        statement = statement.where(Farm.farmer_id == farmer_id)

    if crop_cycle_id is not None:
        statement = statement.where(CropCycle.id == crop_cycle_id)

    inserted = 0

    try:
        cycles = db.scalars(statement).all()

        for cycle in cycles:
            due_tasks = get_scheduled_preplant_tasks(
                crop_name=cycle.crop_name,
                planting_date=cycle.planting_date,
                reference_date=target_date,
            )

            for task in due_tasks:
                # Check this item specifically; several may share a due date.
                existing = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.source_rule_type == "preplant_checklist",
                        DailyTask.title == task["title"],
                    )
                )

                if existing is not None:
                    continue

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=task["title"],
                        description=task["description"],
                        status="pending",
                        source_rule_type="preplant_checklist",
                        source_rule_id=None,
                    )
                )
                inserted += 1

        db.commit()
        return inserted

    except Exception:
        db.rollback()
        raise
