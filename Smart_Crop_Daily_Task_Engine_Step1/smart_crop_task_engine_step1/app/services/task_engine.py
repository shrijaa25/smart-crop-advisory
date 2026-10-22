from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.excel_task_schedule import (
    get_review_only_drench_details,
    get_safe_monitoring_task_details,
)
from app.services.fertilizer_rules import get_fertilizer_alerts
from app.models import (
    CropCycle,
    CropStageRule,
    DailyTask,
    Farm,
    FertilizerRule,
    IrrigationRule,
    WeatherRecord,
)


def generate_daily_monitoring_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
    crop_cycle_id: int | None = None,
) -> int:
    """Create one safe monitoring task per active crop cycle and date.

    Days 1-30 use an eligible Excel monitoring rule when available.
    Day 0 and dates without a matching Excel rule use generic monitoring.
    Unverified treatment rules are never activated here.
    """
    if target_date is None:
        target_date = date.today()

    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(
            Farm.farmer_id == farmer_id
        )

    if crop_cycle_id is not None:
        cycle_statement = cycle_statement.where(
            CropCycle.id == crop_cycle_id
        )

    inserted = 0
    try:
        for cycle in db.scalars(cycle_statement).all():
            # Day 0 is the planting/transplanting date. Do not create tasks
            # before planting.
            if target_date < cycle.planting_date:
                continue

            crop_age = (target_date - cycle.planting_date).days

            # Preserve duplicate prevention, including completed tasks.
            existing = db.scalar(
                select(DailyTask.id).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.task_date == target_date,
                    DailyTask.source_rule_type == "daily_monitoring",
                )
            )
            if existing is not None:
                continue

            # Use the Excel schedule for days 1 through 30.
            excel_task = None
            if 1 <= crop_age <= 30:
                excel_task = get_safe_monitoring_task_details(
                    cycle.crop_name,
                    crop_age,
                )

            if excel_task is not None:
                title = excel_task.get("title") or "Daily crop monitoring"
                description = (
                    excel_task.get("description")
                    or "Inspect your crop and record unusual symptoms."
                )

                trigger_timing = excel_task.get("trigger_timing")
                if trigger_timing:
                    description += f" Timing: {trigger_timing}"

                weather_gate = excel_task.get("weather_gate")
                if weather_gate:
                    description += f" Weather guidance: {weather_gate}"
            else:
                # Preserve the existing generic task as a fallback.
                title = "Daily crop monitoring"
                description = (
                    "Inspect your crop for visible changes or damage. "
                    "Observe soil moisture and whether irrigation may be "
                    "needed. Record unusual symptoms or growth changes; "
                    "add observations or take a photo when useful."
                )

            if 1 <= crop_age <= 30:
                drench_rows = get_review_only_drench_details(
                    cycle.crop_name,
                    crop_age,
                )
                for drench_row in drench_rows:
                    source_fields = "\n".join(
                        f"{column}: "
                        f"{str(value).strip() if value is not None and str(value).strip() else '(blank)'}"
                        for column, value in drench_row.items()
                    )
                    description += (
                        "\n\nDRENCH_DAY_1_30 source details "
                        "(review only; not an instruction to apply):\n"
                        f"{source_fields}\n"
                        "This drench entry is not approved for use unless "
                        "its review status and product guidance are verified."
                    )

            db.add(
                DailyTask(
                    crop_cycle_id=cycle.id,
                    task_date=target_date,
                    title=title,
                    description=description,
                    status="pending",
                    source_rule_type="daily_monitoring",
                    # Excel rule IDs are strings, not database rule IDs.
                    source_rule_id=None,
                )
            )
            inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_daily_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create safe fertigation review reminders for eligible crop stages.

    Safety:
    - Only verified and active fertilizer rules qualify.
    - Fertilizer stage totals are never presented as per-event doses.
    - Existing tasks are not duplicated.
    - No tasks are generated for dates before transplanting.
    """
    if target_date is None:
        target_date = date.today()

    inserted = 0
    scheduled_reminders: set[tuple[int, str]] = set()
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)
    crop_cycles = db.scalars(cycle_statement).all()

    try:
        for cycle in crop_cycles:
            # Crop age starts at day 0 on the transplanting date.
            crop_age = (target_date - cycle.planting_date).days
            if crop_age < 0:
                continue

            rules = db.scalars(
                select(FertilizerRule).where(
                    FertilizerRule.crop_name == cycle.crop_name,
                    FertilizerRule.is_active.is_(True),
                    FertilizerRule.verification_status == "verified",
                    FertilizerRule.day_start.is_not(None),
                    FertilizerRule.day_end.is_not(None),
                    FertilizerRule.day_start <= crop_age,
                    FertilizerRule.day_end >= crop_age,
                )
            ).all()

            for rule in rules:
                # Only the explicitly understood 3-day cadence is scheduled.
                frequency = (rule.frequency or "").strip().lower()
                if "once every 3 days" not in frequency:
                    continue

                stage_start = rule.day_start
                if stage_start is None or (crop_age - stage_start) % 3 != 0:
                    continue

                stage_name = rule.stage_name or "Current crop stage"
                method = rule.application_method or "application"
                title = f"Review {method} plan: {stage_name}"
                reminder_key = (cycle.id, title)

                # SessionLocal disables autoflush, so this in-memory check
                # prevents duplicate pending inserts within this same run.
                if reminder_key in scheduled_reminders:
                    continue

                duplicate = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.title == title,
                        DailyTask.source_rule_type == "fertilizer_stage",
                    )
                )
                if duplicate is not None:
                    scheduled_reminders.add(reminder_key)
                    continue

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description=(
                            "Review the approved crop-specific application plan "
                            "before proceeding. The stored fertilizer amount is "
                            "a total for the stage, not a dose for this individual "
                            "event. Do not apply fertilizer based on this reminder alone."
                        ),
                        status="pending",
                        source_rule_type="fertilizer_stage",
                        source_rule_id=rule.id,
                    )
                )
                scheduled_reminders.add(reminder_key)
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_fertilizer_review_alerts(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create review-only fertilizer reminders from the Python schedule rules."""
    target_date = target_date or date.today()
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(
            CropCycle.status == "active",
            CropCycle.planting_date <= target_date,
        )
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)

    inserted = 0
    try:
        for cycle in db.scalars(cycle_statement).all():
            crop_age = (target_date - cycle.planting_date).days
            alerts = get_fertilizer_alerts(
                cycle.crop_name,
                days_after_transplanting=crop_age,
            )
            for alert in alerts:
                stage = alert["stage"]
                title = (
                    f"Review fertilizer schedule: {cycle.crop_name} ({stage})"
                )
                duplicate = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.source_rule_type == "fertilizer_review",
                        DailyTask.title == title,
                    )
                )
                if duplicate is not None:
                    continue

                fertilizer_lines = []
                for fertilizer in alert["fertilizers"]:
                    details = [fertilizer["name"]]
                    if fertilizer.get("dose_per_day_per_acre"):
                        details.append(
                            "dose/day/acre: "
                            f"{fertilizer['dose_per_day_per_acre']}"
                        )
                    if fertilizer.get("quantity_per_acre"):
                        details.append(
                            f"quantity/acre: {fertilizer['quantity_per_acre']}"
                        )
                    if fertilizer.get("source_quantity"):
                        details.append(
                            f"source quantity: {fertilizer['source_quantity']}"
                        )
                    if fertilizer.get("one_time_dat") is not None:
                        details.append(
                            f"one-time timing: day {fertilizer['one_time_dat']} DAT"
                        )
                    if fertilizer.get("quantity_per_hectare"):
                        details.append(
                            "quantity/hectare: "
                            f"{fertilizer['quantity_per_hectare']}"
                        )
                    if fertilizer.get("note"):
                        details.append(f"note: {fertilizer['note']}")
                    if fertilizer.get("quantity_note"):
                        details.append(f"note: {fertilizer['quantity_note']}")
                    fertilizer_lines.append("; ".join(details))

                description_parts = [
                    "Status: Review Schedule (review required).",
                    f"Schedule window: {stage}.",
                    "Source-listed entries:",
                    *fertilizer_lines,
                ]
                if alert.get("note"):
                    description_parts.append(alert["note"])
                if alert["crop"] == "chilli":
                    description_parts.append(
                        f"Current crop age: day {crop_age} after transplanting."
                    )
                description_parts.append(
                    "These source entries have not been verified as application "
                    "instructions. Review them with a qualified local adviser; "
                    "do not apply fertilizer based on this reminder alone."
                )

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description="\n".join(description_parts),
                        status="pending",
                        source_rule_type="fertilizer_review",
                        source_rule_id=None,
                    )
                )
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_irrigation_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create irrigation review reminders only with unambiguous dry-day data."""
    if target_date is None:
        target_date = date.today()

    inserted = 0
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)
    cycles = db.scalars(cycle_statement).all()

    try:
        start = datetime.combine(target_date, time.min)
        end = start + timedelta(days=1)

        for cycle in cycles:
            farm = db.get(Farm, cycle.farm_id)
            if farm is None:
                continue

            rules = db.scalars(
                select(IrrigationRule).where(
                    IrrigationRule.crop_name == cycle.crop_name,
                    IrrigationRule.is_active.is_(True),
                    IrrigationRule.verification_status == "verified",
                )
            ).all()
            if not rules:
                continue

            weather = db.scalar(
                select(WeatherRecord)
                .where(
                    WeatherRecord.farm_id == farm.id,
                    WeatherRecord.observed_at >= start,
                    WeatherRecord.observed_at < end,
                )
                .order_by(WeatherRecord.observed_at.desc())
            )
            # Missing, nonzero, or unknown rainfall does not qualify as dry.
            if weather is None or weather.rainfall_mm != 0:
                continue

            for rule in rules:
                # Free-text restrictions are not safely machine-interpreted.
                if rule.weather_constraints and rule.weather_constraints.strip():
                    continue

                title = f"Review irrigation plan: {cycle.crop_name}"
                duplicate = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.source_rule_type == "irrigation",
                        DailyTask.source_rule_id == rule.id,
                    )
                )
                if duplicate is not None:
                    continue

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description=(
                            "Review the verified irrigation guidance and check "
                            "field soil moisture before irrigating. This is a "
                            "reminder, not an instruction to apply a specific "
                            "volume of water."
                        ),
                        status="pending",
                        source_rule_type="irrigation",
                        source_rule_id=rule.id,
                        weather_context={
                            "status": "observed",
                            "source": weather.source or "stored_weather_record",
                            "observed_at": weather.observed_at.isoformat(),
                            "rainfall_mm": weather.rainfall_mm,
                            "temperature_c": weather.temperature_c,
                            "humidity_percent": weather.humidity_percent,
                        },
                    )
                )
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_one_time_fertilizer_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create one-time fertilizer reminders for rules with a specific target day.

    This handles fertilizer rules that have a fixed one_time_day (e.g., "apply
    on day 21") rather than a recurring window. Fires exactly once on that day.
    """
    if target_date is None:
        target_date = date.today()

    inserted = 0
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)
    crop_cycles = db.scalars(cycle_statement).all()

    try:
        for cycle in crop_cycles:
            crop_age = (target_date - cycle.planting_date).days
            if crop_age < 0:
                continue

            rules = db.scalars(
                select(FertilizerRule).where(
                    FertilizerRule.crop_name == cycle.crop_name,
                    FertilizerRule.is_active.is_(True),
                    FertilizerRule.verification_status == "verified",
                    FertilizerRule.one_time_day == crop_age,
                )
            ).all()

            for rule in rules:
                fertilizer = rule.fertilizer_name or "fertilizer"
                stage = rule.stage_name or "this stage"
                method = rule.application_method or "application"
                title = f"One-time fertilizer: {fertilizer} ({stage})"

                duplicate = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.title == title,
                        DailyTask.source_rule_type == "fertilizer_onetime",
                    )
                )
                if duplicate is not None:
                    continue

                detail_parts = []
                if rule.amount and rule.unit and rule.area_basis:
                    detail_parts.append(
                        f"Dose: {rule.amount} {rule.unit} per {rule.area_basis}."
                    )
                if rule.instructions:
                    detail_parts.append(rule.instructions)
                detail_parts.append(
                    f"Application method: {method}. "
                    "Always follow the approved crop advisory before applying."
                )

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description=" ".join(detail_parts),
                        status="pending",
                        source_rule_type="fertilizer_onetime",
                        source_rule_id=rule.id,
                    )
                )
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_stage_milestone_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create a daily advisory task whenever a crop enters a new growth stage.

    Fired on the first day of each verified crop-stage window so the farmer
    knows their crop has moved to the next phase.
    """
    if target_date is None:
        target_date = date.today()

    inserted = 0
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)
    crop_cycles = db.scalars(cycle_statement).all()

    try:
        for cycle in crop_cycles:
            crop_age = (target_date - cycle.planting_date).days
            if crop_age < 0:
                continue

            # Only fire on the exact first day of a stage (day_start == crop_age)
            stage_rules = db.scalars(
                select(CropStageRule).where(
                    CropStageRule.crop_name == cycle.crop_name,
                    CropStageRule.verification_status == "verified",
                    CropStageRule.days_basis == "after_transplanting",
                    CropStageRule.day_start == crop_age,
                )
            ).all()

            for rule in stage_rules:
                title = f"New growth stage: {rule.stage_name}"
                duplicate = db.scalar(
                    select(DailyTask.id).where(
                        DailyTask.crop_cycle_id == cycle.id,
                        DailyTask.task_date == target_date,
                        DailyTask.title == title,
                        DailyTask.source_rule_type == "stage_milestone",
                    )
                )
                if duplicate is not None:
                    continue

                db.add(
                    DailyTask(
                        crop_cycle_id=cycle.id,
                        task_date=target_date,
                        title=title,
                        description=(
                            f"Your {cycle.crop_name} has entered the "
                            f"'{rule.stage_name}' stage (day {crop_age}). "
                            "Review the advisory for this stage: check for pest "
                            "and disease signs, confirm your irrigation and "
                            "fertilizer plan for this phase."
                        ),
                        status="pending",
                        source_rule_type="stage_milestone",
                        source_rule_id=rule.id,
                    )
                )
                inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise


def generate_fallback_irrigation_tasks(
    db: Session,
    target_date: date | None = None,
    farmer_id: int | None = None,
) -> int:
    """Create a generic daily irrigation check reminder for every active cycle.

    Unlike generate_irrigation_tasks, this does NOT require a WeatherRecord.
    It fires every day for crops with at least one active verified irrigation
    rule, giving farmers a daily prompt to check field moisture.
    Only one such reminder is created per crop cycle per day.
    """
    if target_date is None:
        target_date = date.today()

    inserted = 0
    cycle_statement = (
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(CropCycle.status == "active")
    )
    if farmer_id is not None:
        cycle_statement = cycle_statement.where(Farm.farmer_id == farmer_id)
    cycles = db.scalars(cycle_statement).all()

    try:
        for cycle in cycles:
            crop_age = (target_date - cycle.planting_date).days
            if crop_age < 0:
                continue

            has_rule = db.scalar(
                select(IrrigationRule.id).where(
                    IrrigationRule.crop_name == cycle.crop_name,
                    IrrigationRule.is_active.is_(True),
                    IrrigationRule.verification_status == "verified",
                )
            )
            if has_rule is None:
                continue

            title = f"Daily irrigation check: {cycle.crop_name}"
            duplicate = db.scalar(
                select(DailyTask.id).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.task_date == target_date,
                    DailyTask.source_rule_type == "irrigation_check",
                )
            )
            if duplicate is not None:
                continue

            db.add(
                DailyTask(
                    crop_cycle_id=cycle.id,
                    task_date=target_date,
                    title=title,
                    description=(
                        "Check soil moisture in your field today. "
                        "Use your local soil and crop guidance to decide whether "
                        "irrigation is needed. This check does not set a universal "
                        "moisture threshold or prescribe an irrigation amount."
                    ),
                    status="pending",
                    source_rule_type="irrigation_check",
                    source_rule_id=None,
                )
            )
            inserted += 1

        db.commit()
        return inserted
    except Exception:
        db.rollback()
        raise
