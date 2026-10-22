from app.services.weather_knowledge import (
    _profile_matches,
    _pesticide_disease_details,
    _qualitative_weather_candidate,
    check_workbook,
    get_weather_advisory_candidates,
    get_workbook_sheets,
    normalise_weather_for_advisory,
)


def test_weather_workbook_exists_and_has_expected_sheets():
    assert check_workbook().is_file()

    sheets = get_workbook_sheets()
    assert "WEATHER_VIRAL_BACTERIAL" in sheets
    assert "WEATHER_DISEASE_RISK" in sheets
    assert "RAW_Prevention" in sheets


def test_weather_normalizer_uses_current_values_for_same_day_observation():
    weather = {
        "status": "available",
        "weather_type": "observed",
        "observation_type": "observed",
        "observed_at": "2026-10-18T10:00",
        "current": {
            "temperature_2m": 31.5,
            "relative_humidity_2m": 72,
        },
        "forecast": {"temperature_max_c": 35, "precipitation_sum_mm": 4},
    }

    result = normalise_weather_for_advisory(weather, "2026-10-18")

    assert result["temperature_c"] == 31.5
    assert result["relative_humidity"] == 72
    assert result["precipitation_mm"] == 4


def test_weather_normalizer_uses_forecast_for_another_date():
    weather = {
        "status": "available",
        "observation_type": "observed",
        "observed_at": "2026-10-18T10:00",
        "current": {
            "temperature_2m": 31.5,
            "relative_humidity_2m": 72,
        },
        "forecast": {"temperature_max_c": 35, "precipitation_sum_mm": 4},
    }

    result = normalise_weather_for_advisory(weather, "2026-10-19")

    assert result["temperature_c"] == 35
    assert result["relative_humidity"] is None
    assert result["precipitation_mm"] == 4


def test_profile_match_ignores_humidity_and_checks_temperature_only():
    profile = "temperature >30" + chr(176) + "C and RH <50%"

    assert _profile_matches(
        profile,
        {"temperature_c": 32, "relative_humidity": 45},
    ) is True
    assert _profile_matches(
        profile,
        {"temperature_c": 32, "relative_humidity": 55},
    ) is True


def test_profile_without_explicit_threshold_is_unknown():
    profile = "above 30" + chr(176) + "C may slow progress"

    assert _profile_matches(profile, {"temperature_c": 35}) is None


def test_todays_forecast_uses_current_temperature_for_risk_rules():
    raw_weather = {
        "status": "available",
        "weather_type": "forecast",
        "target_date": "2026-10-18",
        "observation_type": "observed",
        "observed_at": "2026-10-18T18:45",
        "forecast": {
            "temperature_max_c": 32.5,
            "temperature_min_c": 22.9,
            "precipitation_sum_mm": 0,
        },
        "current": {
            "temperature_2m": 28.3,
            "relative_humidity_2m": 47,
            "precipitation": 0,
        },
    }

    normalized = normalise_weather_for_advisory(raw_weather, "2026-10-18")
    result = get_weather_advisory_candidates("tomato", normalized)

    assert normalized["temperature_c"] == 28.3
    assert normalized["relative_humidity"] == 47
    assert normalized["temperature_source"] == "current_temperature"
    assert result["status"] == "ok"
    assert {item["risk"] for item in result["risk_candidates"]} == {
        "Early Blight",
        "Fusarium wilt",
        "Bacterial wilt",
        "Bacterial Canker",
        "Leaf Curl",
    }
    assert all(
        item["diagnosis_confirmed"] is False
        for item in result["risk_candidates"]
    )
    assert all(
        item["chemical_advice_enabled"] is False
        for item in result["risk_candidates"]
    )
    assert all(
        "pesticide_disease_details" not in item
        for item in result["risk_candidates"]
    )


def test_future_date_does_not_borrow_current_humidity():
    raw_weather = {
        "status": "available",
        "weather_type": "forecast",
        "observation_type": "observed",
        "observed_at": "2026-10-18T18:45",
        "forecast": {"temperature_max_c": 32.5, "precipitation_sum_mm": 0},
        "current": {"temperature_2m": 28.3, "relative_humidity_2m": 47},
    }

    normalized = normalise_weather_for_advisory(raw_weather, "2026-10-20")

    assert normalized["temperature_c"] == 32.5
    assert normalized["relative_humidity"] is None


def test_hot_dry_candidates_include_workbook_marathi_chemical_and_brand_fields():
    result = get_weather_advisory_candidates(
        "tomato",
        {
            "status": "available",
            "temperature_c": 32.5,
            "relative_humidity": 47,
            "precipitation_mm": 0,
        },
    )
    by_name = {item["risk"]: item for item in result["risk_candidates"]}
    leaf_curl = by_name["Leaf Curl"]
    assert leaf_curl["marathi_name"] == "बोकड्या"
    assert "Imidacloprid 17.8% SL" in leaf_curl["chemical_control"]
    assert "Tatamida" in leaf_curl["chemical_brand_name"]
    assert leaf_curl["treatment_review_status"] == "needs_review"
    assert leaf_curl["chemical_advice_enabled"] is False


def test_tomato_spotted_wilt_without_temperature_rule_is_not_alerted():
    result = get_weather_advisory_candidates(
        "tomato",
        {"status": "available", "temperature_c": 32.5},
    )

    assert "Tomato Spotted Wilt" not in {
        item["risk"] for item in result["risk_candidates"]
    }


def test_treatment_lookup_matches_crop_and_disease_after_assessment():
    details = _pesticide_disease_details("chilli", "Early Blight")

    assert details["chemical_name"] == "Mancozeb 75%"
    assert details["brand_name"] == "Indofil M-45 / Dithane M-45"
    assert details["review_status"] == "needs_review"

    missing = _pesticide_disease_details("chilli", "not a workbook disease")
    assert missing["review_status"] == "unavailable"


def test_temperature_range_matches_value_inside_range():
    assert _profile_matches(
        "30–35°C favorable range",
        {"temperature_c": 32.5},
    ) is True


def test_temperature_range_rejects_value_outside_range():
    assert _profile_matches(
        "30–35°C favorable range",
        {"temperature_c": 28.0},
    ) is False


def test_humidity_only_profile_does_not_match_temperature_rules():
    profile = "RH above 85–90%"
    assert _profile_matches(
        profile,
        {"temperature_c": 32, "relative_humidity": 91},
    ) is None


def test_missing_humidity_threshold_stays_unknown():
    assert _profile_matches(
        "No numeric RH threshold supplied",
        {"relative_humidity": 91},
    ) is None
    assert _profile_matches(
        "RH >85%",
        {},
    ) is None


def test_soil_temperature_range_is_not_compared_with_air_temperature():
    assert _profile_matches(
        "Soil 25–32°C",
        {"temperature_c": 27.0},
    ) is None


def test_raw_prevention_uses_same_numeric_range_matcher():
    assert _qualitative_weather_candidate(
        "Temperature 30–35°C",
        {"temperature_c": 32.5},
    ) is True
    assert _qualitative_weather_candidate(
        "Hot, wet, humid conditions",
        {"temperature_c": 32.5, "relative_humidity": 90},
    ) is False


def test_twenty_degrees_only_matches_overlapping_excel_temperature_rule():
    result = get_weather_advisory_candidates(
        "tomato",
        {"status": "available", "temperature_c": 20},
    )

    assert [item["risk"] for item in result["risk_candidates"]] == [
        "Damping Off",
        "Septoria Leaf Spot",
        "Late Blight",
    ]


def test_chilli_rules_match_workbook_at_twenty_twenty_eight_and_thirty_two():
    expected = {
        20: ["Damping Off", "Septoria Leaf Spot", "Late Blight"],
        28: [
            "Early Blight",
            "Fusarium wilt",
            "Bacterial wilt",
            "Bacterial Canker",
            "Leaf Curl",
        ],
        32: [
            "Fusarium wilt",
            "Bacterial wilt",
            "Leaf Curl",
        ],
    }

    for temperature, expected_risks in expected.items():
        result = get_weather_advisory_candidates(
            "chilli",
            {"status": "available", "temperature_c": temperature},
        )
        assert [item["risk"] for item in result["risk_candidates"]] == expected_risks
