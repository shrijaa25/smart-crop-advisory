
"""Read safe daily monitoring tasks from the Excel schedule.

This module only reads schedule data. It does not create database tasks
or activate fertilizer, pesticide, or drench recommendations.
"""

from __future__ import annotations

import re
from typing import Any

from app.knowledge_base.excel_rule_loader import (
    load_day_1_30_tasks,
    load_drench_day_1_30_rules,
)


SAFE_MONITORING_STATUS = "active_safe_task"
MONITORING_TASK_TYPE = "monitoring"


def _is_active(value: Any) -> bool:
    """Interpret common Excel boolean representations safely."""
    return value is True or str(value).strip().lower() in {
        "true",
        "1",
        "yes",
    }


def _crop_matches(crop_scope: Any, crop_name: str) -> bool:
    """Match a crop against semicolon-separated Excel crop names."""
    requested_crop = (crop_name or "").strip().lower()
    if not requested_crop:
        return False

    supplied_crops = [
        item.strip().lower()
        for item in str(crop_scope or "").split(";")
        if item.strip()
    ]

    return requested_crop in supplied_crops


def get_safe_monitoring_task(
    crop_name: str,
    dat: int,
) -> dict[str, Any] | None:
    """Return the approved monitoring rule for a crop and DAT.

    DAT is days after transplanting, with day 1 being the first day
    after transplanting. No review-only or treatment rules are returned.
    """
    if dat < 1 or dat > 30:
        return None

    rows = load_day_1_30_tasks()

    for row in rows:
        status = str(row.get("review_status") or "").strip().lower()
        task_type = str(row.get("task_type") or "").strip().lower()

        if status != SAFE_MONITORING_STATUS:
            continue

        if not _is_active(row.get("is_active")):
            continue

        if task_type != MONITORING_TASK_TYPE:
            continue

        if not _crop_matches(row.get("crop_scope"), crop_name):
            continue

        try:
            rule_dat = int(row.get("dat_or_window"))
        except (TypeError, ValueError):
            continue

        if rule_dat == dat:
            return row

    return None


def get_safe_monitoring_task_details(
    crop_name: str,
    dat: int,
) -> dict[str, Any] | None:
    """Return a small, API-friendly representation of a monitoring rule."""
    row = get_safe_monitoring_task(crop_name, dat)
    if row is None:
        return None

    return {
        "rule_id": row.get("task_rule_id"),
        "crop_name": crop_name,
        "dat": dat,
        "title": row.get("task_title"),
        "description": row.get("task_description"),
        "trigger_timing": row.get("trigger_timing"),
        "weather_gate": row.get("weather_gate"),
        "task_type": row.get("task_type"),
        "review_status": row.get("review_status"),
    }


def get_review_only_drench_details(
    crop_name: str,
    dat: int,
) -> list[dict[str, Any]]:
    """Return complete drench source rows matching crop and DAT for display.

    Drench rows remain reference information: this function never filters them
    into executable or approved recommendations.
    """
    if dat < 1 or dat > 30:
        return []

    matching_rows = []
    for row in load_drench_day_1_30_rules():
        if not _crop_matches(row.get("crop_scope"), crop_name):
            continue

        window = str(row.get("dat_window") or "").strip()
        match = re.fullmatch(r"(\d+)\s*(?:[-\u2013\u2014]\s*(\d+))?", window)
        if match is None:
            continue

        first_day = int(match.group(1))
        last_day = int(match.group(2) or first_day)
        if first_day <= dat <= last_day:
            # Return every original sheet column, without blending data from
            # other sheets or treating review-only rows as active rules.
            matching_rows.append(dict(row))

    return matching_rows
