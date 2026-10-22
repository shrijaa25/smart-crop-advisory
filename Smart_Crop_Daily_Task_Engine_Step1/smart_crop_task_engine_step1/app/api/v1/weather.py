from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.weather import get_weather
from app.services.weather_knowledge import (
    get_weather_advisory_candidates,
    normalise_weather_for_advisory,
)

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("")
async def get_weather_by_town(
    town: str = Query(..., min_length=2),
    district: str | None = Query(None, min_length=2),
    state: str = Query("Maharashtra", min_length=2),
    target_date: date | None = Query(None),
    crop: str | None = Query(None),
):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": town.strip(),
                    "count": 10,
                    "language": "en",
                    "countryCode": "IN",
                },
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            raise HTTPException(
                status_code=404,
                detail="Town not found. Try the nearest known town or district.",
            )

        state_lower = state.strip().lower()
        town_lower = town.strip().lower()
        district_lower = district.strip().lower() if district else None

        # Match state and town first; use district to help choose
        # between locations with similar names.
        matching_places = [
            item
            for item in results
            if item.get("country_code") == "IN"
            and (item.get("admin1") or "").strip().lower() == state_lower
        ]

        if not matching_places:
            raise HTTPException(
                status_code=404,
                detail=f"Town not found in {state}. Check the town and state.",
            )

        def location_score(item):
            score = 0

            if (item.get("name") or "").strip().lower() == town_lower:
                score += 4

            if district_lower:
                admin2 = (item.get("admin2") or "").strip().lower()
                if admin2 == district_lower:
                    score += 4
                elif district_lower in admin2 or admin2 in district_lower:
                    score += 2

            return score

        place = max(matching_places, key=location_score)

        latitude = place["latitude"]
        longitude = place["longitude"]

        weather = await get_weather(
            latitude,
            longitude,
            target_date=target_date,
        )

        result = {
            "town": place["name"],
            "district": district or place.get("admin2"),
            "state": place.get("admin1"),
            "country": place.get("country"),
            "latitude": latitude,
            "longitude": longitude,
            "weather": weather,
        }

        # Optional crop-specific weather risk assessment.
        if crop:
            selected_date = (
                target_date or date.today()
            ).isoformat()

            # Keep weather normalization consistent with the crop-cycle risk API.
            advisory_weather = normalise_weather_for_advisory(
                weather,
                selected_date,
            )

            result["advisories"] = get_weather_advisory_candidates(
                crop,
                advisory_weather,
            )

        return result

    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to the weather service.",
        )
    except (ValueError, TypeError, KeyError):
        raise HTTPException(
            status_code=503,
            detail="Weather data could not be processed.",
        )
