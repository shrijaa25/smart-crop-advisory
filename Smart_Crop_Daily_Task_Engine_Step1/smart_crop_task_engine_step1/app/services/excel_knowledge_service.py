
"""Read-only service for the Smart Crop Excel knowledge base.

This module exposes pre-planting tasks, daily monitoring tasks,
weather/disease risks, fertilizer schedules, source references,
and CNN data requirements.

It does not activate or prescribe unverified treatments.
"""

from __future__ import annotations

from typing import Any

from app.knowledge_base.excel_rule_loader import (
    load_weather_disease_rules,
    load_day_1_30_tasks,
    load_preplant_tasks,
    load_fertilizer_rules,
    load_raw_prevention,
    load_raw_pesticide_disease_rules,
    load_raw_pesticide_pest_rules,
    load_source_rules_review,
    load_cnn_data_requirements,
)


def _is_active(value: Any) -> bool:
    """Interpret common Excel boolean values."""
    return (
        value is True
        or str(value).strip().lower() in {"true", "1", "yes"}
    )


def get_excel_knowledge_summary() -> dict[str, int]:
    """Return the number of records available in each Excel data source."""
    fertilizer = load_fertilizer_rules()

    return {
        "weather_disease_risks": len(load_weather_disease_rules()),
        "preplant_tasks": len(load_preplant_tasks()),
        "day_1_30_tasks": len(load_day_1_30_tasks()),
        "prevention_references": len(load_raw_prevention()),
        "disease_control_references": len(
            load_raw_pesticide_disease_rules()
        ),
        "pest_control_references": len(
            load_raw_pesticide_pest_rules()
        ),
        "source_review_records": len(load_source_rules_review()),
        "cnn_data_requirements": len(load_cnn_data_requirements()),
        "chilli_fertilizer_records": len(fertilizer["chilli"]),
        "tomato_fertilizer_records": len(fertilizer["tomato"]),
        "fertilizer_task_windows": len(fertilizer["task_windows"]),
    }


def get_preplant_task_records() -> list[dict[str, Any]]:
    """Return pre-planting records with their review status preserved."""
    return load_preplant_tasks()


def get_weather_disease_risk_records() -> list[dict[str, Any]]:
    """Return source weather/disease risk records for inspection."""
    return load_weather_disease_rules()


def get_daily_schedule_records() -> list[dict[str, Any]]:
    """Return all day 1–30 records, including review-only entries."""
    return load_day_1_30_tasks()


def get_fertilizer_schedule_records() -> dict[str, list[dict[str, Any]]]:
    """Return fertilizer data without activating recommendations."""
    return load_fertilizer_rules()


def get_prevention_and_pest_disease_references() -> dict[str, Any]:
    """Return source references for review, not automatic treatment."""
    return {
        "prevention": load_raw_prevention(),
        "disease_control": load_raw_pesticide_disease_rules(),
        "pest_control": load_raw_pesticide_pest_rules(),
        "source_review": load_source_rules_review(),
    }


def get_cnn_data_requirements() -> list[dict[str, Any]]:
    """Return the documented image-model data requirements."""
    return load_cnn_data_requirements()


def get_active_safe_monitoring_records() -> list[dict[str, Any]]:
    """Return only explicitly active, approved safe monitoring tasks."""
    safe_records = []

    for row in load_day_1_30_tasks():
        status = str(row.get("review_status") or "").strip().lower()
        task_type = str(row.get("task_type") or "").strip().lower()

        if status != "active_safe_task":
            continue

        if not _is_active(row.get("is_active")):
            continue

        if task_type != "monitoring":
            continue

        safe_records.append(row)

    return safe_records


def get_active_approved_preplant_tasks() -> list[dict[str, Any]]:
    """Return only pre-planting tasks explicitly approved and activated.

    Unreviewed records are excluded. This function does not activate
    or prescribe any treatment.
    """
    approved_tasks = []

    for row in load_preplant_tasks():
        status = str(row.get("review_status") or "").strip().lower()

        if status not in {"verified", "approved"}:
            continue

        if not _is_active(row.get("is_active")):
            continue

        approved_tasks.append(row)

    return approved_tasks
