"""Code-defined fertilizer schedule references transcribed from supplied sources.

All chilli schedule entries still require agronomic review. These records are
for review reminders only and must not be treated as fertilizer instructions.
"""

from __future__ import annotations


def _source_entry(
    name: str,
    *,
    dose_per_day_per_acre: str | None = None,
    quantity_per_acre: str | None = None,
    source_quantity: str | None = None,
    quantity_note: str | None = None,
    one_time_dat: int | None = None,
) -> dict[str, str | int]:
    entry: dict[str, str | int] = {"name": name}
    if dose_per_day_per_acre is not None:
        entry["dose_per_day_per_acre"] = dose_per_day_per_acre
    if quantity_per_acre is not None:
        entry["quantity_per_acre"] = quantity_per_acre
    if source_quantity is not None:
        entry["source_quantity"] = source_quantity
    if quantity_note is not None:
        entry["quantity_note"] = quantity_note
    if one_time_dat is not None:
        entry["one_time_dat"] = one_time_dat
    return entry


FERTILIZER_RULES: dict[str, list[dict]] = {
    "chilli": [
        {
            "start_dat": 3,
            "end_dat": 30,
            "fertilizers": [
                _source_entry(
                    "MgSO4",
                    dose_per_day_per_acre="200 gm/day/acre",
                    quantity_per_acre="5.4 kg/acre",
                ),
                _source_entry(
                    "Urea",
                    dose_per_day_per_acre="400 gm/day/acre",
                    quantity_per_acre="10.8 kg/acre",
                ),
                _source_entry(
                    "19:19:19",
                    dose_per_day_per_acre="2 kg/day/acre",
                    quantity_per_acre="27 kg/acre",
                ),
                _source_entry(
                    "Boron 20%",
                    source_quantity="400 gm",
                    quantity_note="Source quantity-column alignment is unclear.",
                    one_time_dat=20,
                ),
            ],
        },
        {
            "start_dat": 31,
            "end_dat": 60,
            "fertilizers": [
                _source_entry(
                    "Urea",
                    dose_per_day_per_acre="400 gm/day/acre",
                    quantity_per_acre="18 kg/acre",
                ),
                _source_entry(
                    "12:61:00",
                    dose_per_day_per_acre="600 gm/day/acre",
                    quantity_per_acre="12 kg/acre",
                ),
                _source_entry(
                    "MOP (white colour)",
                    dose_per_day_per_acre="800 gm/day/acre",
                    quantity_per_acre="21 kg/acre",
                ),
                _source_entry(
                    "MgSO4",
                    dose_per_day_per_acre="400 gm/day/acre",
                    quantity_per_acre="12 kg/acre",
                ),
                _source_entry(
                    "Calcium nitrate",
                    quantity_per_acre="5 kg per acre, one time",
                    one_time_dat=40,
                ),
                _source_entry(
                    "Boron 20%",
                    source_quantity="400 gm",
                    quantity_note="Source quantity-column alignment is unclear.",
                    one_time_dat=60,
                ),
            ],
        },
        {
            "start_dat": 61,
            "end_dat": 90,
            "fertilizers": [
                _source_entry(
                    "Urea",
                    dose_per_day_per_acre="1.6 kg/day/acre",
                    quantity_per_acre="48 kg/acre",
                ),
                _source_entry(
                    "12:61:00",
                    dose_per_day_per_acre="500 gm/day/acre",
                    quantity_per_acre="9 kg/acre",
                ),
                _source_entry(
                    "MOP (white colour)",
                    dose_per_day_per_acre="1.2 kg/day/acre",
                    quantity_per_acre="36 kg/acre",
                ),
                _source_entry(
                    "MgSO4",
                    dose_per_day_per_acre="600 gm/day/acre",
                    quantity_per_acre="18 kg/acre",
                ),
                _source_entry(
                    "Calcium nitrate",
                    quantity_per_acre="5 kg per acre, one time",
                    one_time_dat=80,
                ),
                _source_entry(
                    "Boron 20%",
                    source_quantity="400 gm",
                    quantity_note="Source quantity-column alignment is unclear.",
                    one_time_dat=90,
                ),
            ],
        },
        {
            "start_dat": 91,
            "end_dat": 120,
            "fertilizers": [
                _source_entry(
                    "Ammonium sulphate",
                    dose_per_day_per_acre="1.5 kg/day/acre",
                    quantity_per_acre="45 kg/acre",
                ),
                _source_entry(
                    "Urea",
                    dose_per_day_per_acre="2 kg/day/acre",
                    quantity_per_acre="60 kg/acre",
                ),
                _source_entry(
                    "0:52:34",
                    dose_per_day_per_acre="1 kg/day/acre",
                    quantity_per_acre="30 kg/acre",
                ),
                _source_entry(
                    "MgSO4",
                    dose_per_day_per_acre="600 gm/day/acre",
                    quantity_per_acre="18 kg/acre",
                ),
                _source_entry(
                    "Calcium nitrate",
                    quantity_per_acre="5 kg per acre, one time",
                    one_time_dat=100,
                ),
                _source_entry(
                    "Boron 20%",
                    source_quantity="400 gm",
                    quantity_note="Source quantity-column alignment is unclear.",
                    one_time_dat=110,
                ),
            ],
        },
        {
            "start_dat": 121,
            "end_dat": 180,
            "fertilizers": [
                _source_entry(
                    "Ammonium sulphate",
                    dose_per_day_per_acre="2.5 kg/day/acre",
                    quantity_per_acre="75 kg/acre",
                ),
                _source_entry(
                    "MOP (white colour)",
                    dose_per_day_per_acre="600 gm/day/acre",
                    quantity_per_acre="18 kg/acre",
                ),
                _source_entry(
                    "13:00:45",
                    dose_per_day_per_acre="600 gm/day/acre",
                    quantity_per_acre="18 kg/acre",
                ),
            ],
        },
    ],
    "tomato": [
        {
            "start_dat": None,
            "end_dat": None,
            "stage": "Overall requirement (no date-specific schedule)",
            "fertilizers": [
                {
                    "name": "NPK",
                    "quantity_per_hectare": "200:250:250 kg/ha (N:P2O5:K2O)",
                    "note": "Overall requirement recorded in the supplied source.",
                },
                {
                    "name": "Phosphorus",
                    "note": "Source notes that 75% of total phosphorus is applied basally.",
                },
            ],
            "note": (
                "No complete stage-wise tomato fertilizer schedule is available. "
                "Do not infer date-specific application timings or doses."
            ),
        }
    ],
}


def get_fertilizer_alerts(
    crop_name: str,
    days_after_transplanting: int,
) -> list[dict]:
    """Return source schedule details for review at this crop age."""
    crop = (crop_name or "").strip().lower()
    if crop == "chili":
        crop = "chilli"
    if crop not in FERTILIZER_RULES:
        return []

    alerts = []
    for rule in FERTILIZER_RULES[crop]:
        start = rule.get("start_dat")
        end = rule.get("end_dat")

        # Tomato has an overall reference, not a DAT schedule. Return it as
        # review information without presenting an application milestone.
        if start is None and end is None:
            alerts.append(
                {
                    "crop": crop,
                    "days_after_transplanting": days_after_transplanting,
                    "stage": rule["stage"],
                    "fertilizers": rule["fertilizers"],
                    "note": rule["note"],
                    "status": "review_required",
                    "alert_type": "fertilizer_schedule",
                }
            )
            continue

        if start is None or end is None:
            continue
        if not start <= days_after_transplanting <= end:
            continue

        due_fertilizers = [
            fertilizer
            for fertilizer in rule["fertilizers"]
            if fertilizer.get("one_time_dat") is None
            or fertilizer["one_time_dat"] == days_after_transplanting
        ]
        if not due_fertilizers:
            continue

        alerts.append(
            {
                "crop": crop,
                "days_after_transplanting": days_after_transplanting,
                "stage": f"{start}-{end} DAT",
                "fertilizers": due_fertilizers,
                "status": "review_required",
                "alert_type": "fertilizer_schedule",
            }
        )
    return alerts
