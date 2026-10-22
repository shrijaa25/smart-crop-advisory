from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import CropCycle, DailyTask, Farm, Farmer
from app.services.preplant_checklist import (
    generate_preplant_checklist_tasks,
    get_preplant_checklist,
    get_scheduled_preplant_tasks,
)


def test_tomato_has_six_preplant_tasks():
    tasks = get_preplant_checklist("tomato")
    assert len(tasks) == 6


def test_chilli_has_six_preplant_tasks():
    tasks = get_preplant_checklist("chilli")
    assert len(tasks) == 6


def test_crop_name_is_case_insensitive():
    assert get_preplant_checklist("TOMATO") == (
        get_preplant_checklist("tomato")
    )


def test_unsupported_crop_returns_empty_list():
    assert get_preplant_checklist("wheat") == []


def test_every_task_has_a_planting_offset():
    for crop in ("tomato", "chilli"):
        for task in get_preplant_checklist(crop):
            assert task["days_before_planting"] > 0
            assert task["title"]
            assert task["description"]


def test_checklist_contains_no_treatment_instructions():
    for crop in ("tomato", "chilli"):
        for task in get_preplant_checklist(crop):
            assert "chemical_dose" not in task
            assert "pesticide" not in task
            assert "fertilizer_dose" not in task


def test_preplant_tasks_are_scheduled_for_their_due_date():
    planting_date = date(2026, 11, 20)

    tasks = get_scheduled_preplant_tasks(
        "tomato",
        planting_date,
        reference_date=date(2026, 11, 13),
    )

    assert len(tasks) == 2
    assert all(task["due_date"] == date(2026, 11, 13) for task in tasks)


def test_preplant_tasks_are_not_returned_after_planting():
    tasks = get_scheduled_preplant_tasks(
        "chilli",
        date(2026, 11, 20),
        reference_date=date(2026, 11, 21),
    )

    assert tasks == []


def test_unsupported_crop_has_no_scheduled_tasks():
    tasks = get_scheduled_preplant_tasks(
        "wheat",
        date(2026, 11, 20),
        reference_date=date(2026, 11, 13),
    )

    assert tasks == []


def create_test_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def create_test_crop_cycle(db, crop_name, planting_date):
    farmer = Farmer(full_name="Preplant Test Farmer")
    db.add(farmer)
    db.flush()

    farm = Farm(farmer_id=farmer.id, name="Preplant Test Farm")
    db.add(farm)
    db.flush()

    cycle = CropCycle(
        farm_id=farm.id,
        crop_name=crop_name,
        planting_date=planting_date,
        status="active",
    )
    db.add(cycle)
    db.flush()

    return cycle


def test_generator_creates_due_preplant_tasks():
    engine = create_test_database()

    try:
        with Session(engine) as db:
            cycle = create_test_crop_cycle(
                db,
                "tomato",
                date(2026, 11, 20),
            )
            db.commit()

            created = generate_preplant_checklist_tasks(
                db,
                target_date=date(2026, 11, 13),
                crop_cycle_id=cycle.id,
            )

            tasks = db.scalars(
                select(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.source_rule_type == "preplant_checklist",
                )
            ).all()

            assert created == 2
            assert len(tasks) == 2

    finally:
        engine.dispose()


def test_generator_does_not_create_duplicate_tasks():
    engine = create_test_database()

    try:
        with Session(engine) as db:
            cycle = create_test_crop_cycle(
                db,
                "chilli",
                date(2026, 11, 20),
            )
            db.commit()

            first_count = generate_preplant_checklist_tasks(
                db,
                target_date=date(2026, 11, 13),
                crop_cycle_id=cycle.id,
            )
            second_count = generate_preplant_checklist_tasks(
                db,
                target_date=date(2026, 11, 13),
                crop_cycle_id=cycle.id,
            )

            assert first_count == 2
            assert second_count == 0

    finally:
        engine.dispose()


def test_generator_skips_already_planted_crops():
    engine = create_test_database()

    try:
        with Session(engine) as db:
            cycle = create_test_crop_cycle(
                db,
                "tomato",
                date(2026, 11, 10),
            )
            db.commit()

            created = generate_preplant_checklist_tasks(
                db,
                target_date=date(2026, 11, 13),
                crop_cycle_id=cycle.id,
            )

            assert created == 0

    finally:
        engine.dispose()
