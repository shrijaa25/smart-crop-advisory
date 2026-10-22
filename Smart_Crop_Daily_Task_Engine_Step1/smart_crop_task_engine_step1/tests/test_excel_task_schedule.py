
from app.services.excel_task_schedule import (
    get_review_only_drench_details,
    get_safe_monitoring_task,
    get_safe_monitoring_task_details,
)


def test_tomato_day_1_returns_monitoring_rule():
    row = get_safe_monitoring_task("tomato", 1)

    assert row is not None
    assert row["task_rule_id"] == "MON-01"
    assert row["task_type"] == "monitoring"
    assert row["review_status"] == "active_safe_task"


def test_chilli_day_15_returns_monitoring_rule():
    row = get_safe_monitoring_task("chilli", 15)

    assert row is not None
    assert row["task_rule_id"] == "MON-15"


def test_crop_name_matching_is_case_insensitive():
    row = get_safe_monitoring_task("TOMATO", 1)

    assert row is not None
    assert row["task_rule_id"] == "MON-01"


def test_day_outside_schedule_returns_none():
    assert get_safe_monitoring_task("tomato", 0) is None
    assert get_safe_monitoring_task("tomato", 31) is None


def test_unknown_crop_returns_none():
    assert get_safe_monitoring_task("wheat", 1) is None


def test_review_only_drench_rule_is_not_returned():
    for day in (1, 2, 3, 10, 11, 12, 20, 21, 22, 28, 29, 30):
        row = get_safe_monitoring_task("tomato", day)

        assert row is not None
        assert row["task_type"] == "monitoring"
        assert row["review_status"] == "active_safe_task"


def test_task_details_are_api_friendly():
    details = get_safe_monitoring_task_details("tomato", 1)

    assert details is not None
    assert details["rule_id"] == "MON-01"
    assert details["crop_name"] == "tomato"
    assert details["dat"] == 1
    assert details["title"] == "Daily mandatory monitoring"


def test_day_31_details_return_none():
    assert get_safe_monitoring_task_details("tomato", 31) is None


def test_drench_source_rows_match_crop_and_day_and_keep_every_column():
    day_one = get_review_only_drench_details("tomato", 1)
    day_three = get_review_only_drench_details("chilli", 3)
    day_four = get_review_only_drench_details("tomato", 4)

    assert len(day_one) == 1
    assert day_one[0]["rule_id"] == "DR-01"
    assert day_one[0]["review_status"] == "needs_review"
    assert day_one[0]["is_active"] is False
    assert set(day_one[0]) == {
        "rule_id",
        "crop_scope",
        "stage_name",
        "dat_window",
        "trigger_window",
        "technical_term_as_supplied",
        "solution_mix_as_supplied",
        "volume_per_plant_as_supplied",
        "application_method_as_supplied",
        "objective_as_supplied",
        "compatibility_and_safety_notes",
        "review_status",
        "is_active",
        "source_notes",
    }
    assert day_three[0]["rule_id"] == "DR-01"
    assert day_four == []
