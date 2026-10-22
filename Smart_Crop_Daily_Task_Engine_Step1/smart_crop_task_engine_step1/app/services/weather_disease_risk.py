"""Conservative weather-risk screening for SmartCrop.

Weather conditions cannot confirm that a crop has a disease.
This module only returns inspection alerts.
"""

from __future__ import annotations

from typing import Any


RISK_PROFILES = {
    "damping-off": {
        "temperature_min_c": 18.0,
        "temperature_max_c": 25.0,
        "humidity_min_percent": 90.0,
        "rain_or_wet_soil_required": True,
        "nursery_preferred": True,
    },
    "early blight": {
        "temperature_min_c": 24.0,
        "temperature_max_c": 29.0,
        "humidity_min_percent": 85.0,
        "rain_or_wet_soil_required": True,
    },
    "fusarium wilt": {
        "temperature_min_c": 25.0,
        "temperature_max_c": 32.0,
        "humidity_min_percent": None,
        "rain_or_wet_soil_required": None,
    },
    "septoria leaf spot": {
        "temperature_min_c": 15.0,
        "temperature_max_c": 27.0,
        "humidity_min_percent": 80.0,
        "rain_or_wet_soil_required": True,
    },
    "late blight": {
        "temperature_min_c": 10.0,
        "temperature_max_c": 24.0,
        "humidity_min_percent": 90.0,
        "rain_or_wet_soil_required": True,
    },
    "bacterial wilt": {
        "temperature_min_c": 30.0,
        "temperature_max_c": 35.0,
        "humidity_min_percent": None,
        "rain_or_wet_soil_required": True,
    },
    "bacterial canker": {
        "temperature_min_c": 23.0,
        "temperature_max_c": 30.0,
        "humidity_min_percent": 80.0,
        "rain_or_wet_soil_required": True,
    },
}


def evaluate_weather_disease_risk(
    *,
    crop_name: str,
    weather: dict[str, Any] | None,
    nursery_stage: bool = False,
) -> list[dict[str, Any]]:
    """Return preliminary weather-risk inspection alerts.

    Expected weather format:
    {
        "status": "available",
        "current": {
            "temperature_2m": 25,
            "relative_humidity_2m": 90,
            "precipitation": 1
        },
        "forecast": {
            "precipitation_probability_max_percent": 70
        }
    }

    These thresholds are screening heuristics, not validated
    disease-prediction thresholds.
    """

    crop = (crop_name or "").strip().lower()

    if crop not in {"tomato", "chilli", "chili"}:
        return []

    if not weather or weather.get("status") != "available":
        return [
            {
                "disease": None,
                "risk_status": "unable_to_verify",
                "task_title": "Weather risk unavailable",
                "task_description": (
                    "Weather data is missing or unavailable. "
                    "Inspect your crop routinely. No weather-based "
                    "risk conclusion can be made."
                ),
                "action_type": "inspection_only",
            }
        ]

    current = weather.get("current") or {}
    forecast = weather.get("forecast") or {}

    temperature = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    precipitation = current.get("precipitation")

    rain_probability = forecast.get(
        "precipitation_probability_max_percent"
    )

    if temperature is None:
        return [
            {
                "disease": None,
                "risk_status": "unable_to_verify",
                "task_title": "Weather risk cannot be verified",
                "task_description": (
                    "Temperature is missing from the weather response. "
                    "Continue routine crop inspection."
                ),
                "action_type": "inspection_only",
            }
        ]

    temperature = float(temperature)

    wet = None

    if precipitation is not None:
        wet = float(precipitation) > 0

    if (
        wet is False
        and rain_probability is not None
        and float(rain_probability) >= 60
    ):
        wet = True

    alerts = []

    for disease, profile in RISK_PROFILES.items():

        if disease == "damping-off" and not nursery_stage:
            continue

        minimum_temp = profile["temperature_min_c"]
        maximum_temp = profile["temperature_max_c"]

        if not minimum_temp <= temperature <= maximum_temp:
            continue

        minimum_humidity = profile["humidity_min_percent"]

        if minimum_humidity is not None:

            if humidity is None:
                alerts.append({
                    "disease": disease,
                    "risk_status": "unable_to_verify",
                    "task_title": (
                        f"Check conditions related to {disease}"
                    ),
                    "task_description": (
                        "Temperature is within the screening range, "
                        "but humidity is unavailable. Inspect the crop "
                        "for symptoms; this is not a diagnosis."
                    ),
                    "action_type": "inspection_only",
                })
                continue

            if float(humidity) < minimum_humidity:
                continue

        wet_required = profile["rain_or_wet_soil_required"]

        if wet_required is True and wet is not True:

            if wet is None:
                alerts.append({
                    "disease": disease,
                    "risk_status": "unable_to_verify",
                    "task_title": (
                        f"Check wetness-related risk for {disease}"
                    ),
                    "task_description": (
                        "Rainfall or leaf-wetness information is "
                        "insufficient. Inspect the crop and soil."
                    ),
                    "action_type": "inspection_only",
                })

            continue

        alerts.append({
            "disease": disease,
            "risk_status": "elevated_weather_risk",
            "task_title": f"Inspect crop for {disease} symptoms",
            "task_description": (
                f"Weather conditions match a preliminary screening "
                f"profile for {disease}. Inspect the crop for visible "
                "symptoms. Weather alone cannot confirm disease. "
                "Do not apply pesticide solely because of this alert."
            ),
            "action_type": "inspection_only",
        })

    return alerts