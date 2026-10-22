"""Open-Meteo adapter with date-specific weather and provenance."""

from datetime import date, datetime, timedelta, timezone

import httpx


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


async def get_weather(
    latitude: float | None,
    longitude: float | None,
    target_date: date | None = None,
) -> dict:
    """Fetch current weather or weather for a selected date.

    Today and future dates use forecast data.
    Past dates use historical archive data.
    Missing weather is reported as unavailable, never guessed.
    """
    if latitude is None or longitude is None:
        return {
            "status": "unavailable",
            "reason": "Farm coordinates are not set.",
            "source": "open-meteo",
        }

    target_date = target_date or datetime.now().date()
    today = datetime.now().date()

    if target_date > today + timedelta(days=15):
        return {
            "status": "unavailable",
            "reason": "The selected date is outside the forecast range.",
            "source": "open-meteo",
            "target_date": target_date.isoformat(),
        }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            if target_date < today:
                response = await client.get(
                    ARCHIVE_URL,
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "start_date": target_date.isoformat(),
                        "end_date": target_date.isoformat(),
                        "daily": (
                            "precipitation_sum,"
                            "temperature_2m_max,"
                            "temperature_2m_min"
                        ),
                        "timezone": "auto",
                    },
                )
                source = "open-meteo-archive"
                weather_type = "historical"
            else:
                response = await client.get(
                    FORECAST_URL,
                    params={
                        "latitude": latitude,
                        "longitude": longitude,
                        "current": (
                            "temperature_2m,"
                            "relative_humidity_2m,"
                            "precipitation,"
                            "wind_speed_10m"
                        ),
                        "daily": (
                            "precipitation_probability_max,"
                            "precipitation_sum,"
                            "temperature_2m_max,"
                            "temperature_2m_min"
                        ),
                        "timezone": "auto",
                        "forecast_days": 16,
                    },
                )
                source = "open-meteo-forecast"
                weather_type = "forecast"

            response.raise_for_status()
            data = response.json()

        daily = data.get("daily") or {}
        dates = daily.get("time") or []

        try:
            index = dates.index(target_date.isoformat())
        except ValueError:
            return {
                "status": "unavailable",
                "reason": "Weather is not available for the selected date.",
                "source": source,
                "target_date": target_date.isoformat(),
                "weather_type": weather_type,
            }

        def daily_value(key):
            values = daily.get(key) or []
            return values[index] if index < len(values) else None

        current = data.get("current") or {}
        stamp = current.get("time")

        result = {
            "status": "available",
            "source": source,
            "weather_type": weather_type,
            "target_date": target_date.isoformat(),
            "forecast": {
                "precipitation_probability_max_percent": (
                    daily_value("precipitation_probability_max")
                    if weather_type == "forecast"
                    else None
                ),
                "precipitation_sum_mm": daily_value("precipitation_sum"),
                "temperature_max_c": daily_value("temperature_2m_max"),
                "temperature_min_c": daily_value("temperature_2m_min"),
            },
            "missing_values": [],
        }

        if target_date == today:
            result["observation_type"] = "observed"
            result["observed_at"] = stamp
            result["current"] = {
                key: current.get(key)
                for key in (
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation",
                    "wind_speed_10m",
                )
            }

            offset = timedelta(
                seconds=int(data.get("utc_offset_seconds") or 0)
            )
            observed = (
                datetime.fromisoformat(stamp).replace(
                    tzinfo=timezone(offset)
                )
                if stamp
                else None
            )
            now = datetime.now(timezone.utc)
            stale = (
                observed is None
                or (now - observed).total_seconds() > 3 * 3600
            )
            result["status"] = "stale" if stale else "available"
            if stale:
                result["reason"] = (
                    "Current observation is missing or older than three hours."
                )

        result["missing_values"] = [
            key
            for key, value in result["forecast"].items()
            if value is None
        ]

        return result

    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return {
            "status": "unavailable",
            "source": "open-meteo",
            "target_date": target_date.isoformat(),
            "reason": (
                f"Weather service unavailable: {type(exc).__name__}."
            ),
        }


async def get_weather_for_farm(
    village: str | None,
    district: str | None,
    state: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
    target_date: date | None = None,
) -> dict:
    """Get date-specific weather using farm coordinates or its location name."""

    # Use saved coordinates when available.
    if latitude is not None and longitude is not None:
        return await get_weather(latitude, longitude, target_date)

    # Build a location query from the farmer's saved details.
    location_parts = [
        part.strip()
        for part in (village, district, state, "India")
        if part and part.strip()
    ]

    if not location_parts:
        return {
            "status": "unavailable",
            "source": "open-meteo",
            "reason": "Farm town, district, and state are missing.",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": village or district or state,
                    "count": 10,
                    "language": "en",
                    "countryCode": "IN",
                },
            )
            response.raise_for_status()
            results = response.json().get("results") or []

        # Prefer a result matching the supplied state and district.
        def location_score(item):
            score = 0
            if state and (item.get("admin1") or "").casefold() == state.strip().casefold():
                score += 2
            if district and (item.get("admin2") or "").casefold() == district.strip().casefold():
                score += 2
            if village and (item.get("name") or "").casefold() == village.strip().casefold():
                score += 4
            return score

        if not results:
            return {
                "status": "unavailable",
                "source": "open-meteo",
                "reason": "The farm location could not be found.",
            }

        place = max(results, key=location_score)

        if state and (
            (place.get("admin1") or "").casefold() != state.strip().casefold()
        ):
            return {
                "status": "unavailable",
                "source": "open-meteo",
                "reason": "Could not verify a matching state for the farm location.",
            }

        weather = await get_weather(
            place["latitude"],
            place["longitude"],
            target_date,
        )

        weather["location"] = {
            "name": place.get("name"),
            "district": place.get("admin2"),
            "state": place.get("admin1"),
        }
        return weather

    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        return {
            "status": "unavailable",
            "source": "open-meteo",
            "reason": f"Location or weather lookup failed: {type(exc).__name__}.",
        }
