"""Read and filter fertilizer schedules from Excel."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.knowledge_base.excel_rule_loader import (
    load_fertilizer_rules,
    is_rule_eligible,
)


def crop_age_days(
    transplanting_date: date,
    target_date: date,
) -> int:
    """Calculate crop age using transplanting day as DAT 0."""
    return (target_date - transplanting_date).days


def get_fertilizer_rows_for_crop(
    crop_name: str,
    *,
    workbook_path: str | None = None,
    include_review_only: bool = False,
) -> list[dict[str, Any]]:
    """Return fertilizer reference rows for a crop.

    By default, only active and verified rows are returned.
    Set include_review_only=True to inspect unverified source rows.
    """

    if workbook_path:
        schedules = load_fertilizer_rules(workbook_path)
    else:
        schedules = load_fertilizer_rules()

    crop = (crop_name or "").strip().lower()

    if crop in {"chilli", "chili"}:
        rows = schedules["chilli"]
    elif crop == "tomato":
        rows = schedules["tomato"]
    else:
        return []

    if include_review_only:
        return rows

    return [
        row
        for row in rows
        if is_rule_eligible(row)
    ]


def get_review_task_windows(
    *,
    workbook_path: str | None = None,
) -> list[dict[str, Any]]:
    """Return reference task windows for review, not prescriptions."""

    if workbook_path:
        schedules = load_fertilizer_rules(workbook_path)
    else:
        schedules = load_fertilizer_rules()

    return schedules["task_windows"]


def rows_matching_dat(
    crop_name: str,
    dat: int,
    *,
    workbook_path: str | None = None,
    include_review_only: bool = False,
) -> list[dict[str, Any]]:
    """Match simple numeric DAT ranges or exact DAT values.

    Examples supported:
        31-60 DAT
        31–60 DAT
        20 DAT

    Textual timing descriptions are not automatically interpreted.
    """

    if dat < 0:
        return []

    rows = get_fertilizer_rows_for_crop(
        crop_name,
        workbook_path=workbook_path,
        include_review_only=include_review_only,
    )

    import re

    matched = []

    for row in rows:
        label = str(row.get("stage_or_DAT") or "")

        range_match = re.search(
            r"(\d+)\s*[–-]\s*(\d+)\s*DAT",
            label,
            re.IGNORECASE,
        )

        exact_match = None

        if not range_match:
            exact_match = re.search(
                r"(\d+)\s*DAT",
                label,
                re.IGNORECASE,
            )

        if range_match:
            start_day = int(range_match.group(1))
            end_day = int(range_match.group(2))

            if start_day <= dat <= end_day:
                matched.append(row)

        elif exact_match:
            exact_day = int(exact_match.group(1))

            if exact_day == dat:
                matched.append(row)

    return matched