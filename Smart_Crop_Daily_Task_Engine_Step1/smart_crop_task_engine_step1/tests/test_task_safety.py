from datetime import date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AgriculturalSourceRecord,
    CropCycle,
    CropStageRule,
    DailyTask,
    Farm,
    Farmer,
    FertilizerRule,
    IrrigationRule,
    KnowledgeSource,
    WeatherRecord,
)
from app.services.crop_stage import get_crop_stage
from app.services.task_engine import (
    generate_daily_monitoring_tasks,
    generate_daily_tasks,
    generate_irrigation_tasks,
    generate_stage_milestone_tasks,
)

TARGET_DATE = date(2026, 10, 14)


def setup_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def create_crop_cycle(db: Session, planting_date: date = TARGET_DATE):
    farmer = Farmer(full_name="Test Farmer")
    db.add(farmer)
    db.flush()
    farm = Farm(farmer_id=farmer.id, name="Test Farm")
    db.add(farm)
    db.flush()
    cycle = CropCycle(
        farm_id=farm.id,
        crop_name="tomato",
        planting_date=planting_date,
        status="active",
    )
    db.add(cycle)
    db.flush()
    return farm, cycle


def add_fertilizer_rule(
    db: Session,
    *,
    active: bool,
    verification_status: str,
    fertilizer_name: str = "19:19:19",
):
    rule = FertilizerRule(
        crop_name="tomato",
        stage_name="Plant establishment",
        day_start=0,
        day_end=9,
        days_basis="after_transplanting",
        fertilizer_name=fertilizer_name,
        amount=25,
        unit="kg",
        area_basis="per hectare per stage",
        frequency="once every 3 days during stage",
        application_method="fertigation",
        verification_status=verification_status,
        is_active=active,
    )
    db.add(rule)
    db.flush()
    return rule


def add_irrigation_rule(
    db: Session,
    *,
    active: bool = True,
    verification_status: str = "verified",
    weather_constraints: str | None = None,
):
    rule = IrrigationRule(
        crop_name="tomato",
        verification_status=verification_status,
        is_active=active,
        weather_constraints=weather_constraints,
    )
    db.add(rule)
    db.flush()
    return rule


def test_daily_monitoring_runs_without_stage_rule_and_is_idempotent_per_cycle():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            farm, first_cycle = create_crop_cycle(db)
            second_cycle = CropCycle(
                farm_id=farm.id,
                crop_name="tomato",
                planting_date=TARGET_DATE,
                status="active",
            )
            inactive_cycle = CropCycle(
                farm_id=farm.id,
                crop_name="chilli",
                planting_date=TARGET_DATE,
                status="inactive",
            )
            db.add_all([second_cycle, inactive_cycle])
            db.commit()

            stage = get_crop_stage(db, first_cycle.id, TARGET_DATE)
            assert stage["stage_name"] is None
            assert "No verified crop-stage rule" in stage["message"]

            assert generate_daily_monitoring_tasks(
                db, TARGET_DATE, farmer_id=farm.farmer_id
            ) == 2
            tasks = db.scalars(
                select(DailyTask).where(
                    DailyTask.source_rule_type == "daily_monitoring",
                    DailyTask.task_date == TARGET_DATE,
                )
            ).all()
            assert len(tasks) == 2
            assert {task.crop_cycle_id for task in tasks} == {
                first_cycle.id,
                second_cycle.id,
            }
            assert all("pesticide" not in task.description.lower() for task in tasks)
            assert all("fertilizer" not in task.description.lower() for task in tasks)
            assert all("photo" in task.description.lower() for task in tasks)

            tasks[0].status = "completed"
            db.commit()
            assert generate_daily_monitoring_tasks(
                db, TARGET_DATE, farmer_id=farm.farmer_id
            ) == 0
            db.refresh(tasks[0])
            assert tasks[0].status == "completed"
    finally:
        engine.dispose()


def test_day_one_monitoring_includes_drench_source_as_review_only_and_deduplicates():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(
                db,
                planting_date=TARGET_DATE.replace(day=TARGET_DATE.day - 1),
            )

            assert generate_daily_monitoring_tasks(db, TARGET_DATE) == 1
            task = db.scalar(
                select(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.task_date == TARGET_DATE,
                    DailyTask.source_rule_type == "daily_monitoring",
                )
            )
            assert task is not None
            assert task.title == "Daily mandatory monitoring"
            assert "DRENCH_DAY_1_30 source details (review only" in task.description
            assert "review_status: needs_review" in task.description
            assert "is_active: False" in task.description
            assert "solution_mix_as_supplied:" in task.description
            assert "source_notes:" in task.description
            assert generate_daily_monitoring_tasks(db, TARGET_DATE) == 0

            task.status = "completed"
            db.commit()
            assert generate_daily_monitoring_tasks(db, TARGET_DATE) == 0
            db.refresh(task)
            assert task.status == "completed"
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.task_date == TARGET_DATE,
                )
            ) == 1
    finally:
        engine.dispose()


def test_daily_monitoring_skips_dates_before_transplanting():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(db, planting_date=date(2026, 10, 15))
            assert generate_daily_monitoring_tasks(db, TARGET_DATE) == 0
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id
                )
            ) == 0
    finally:
        engine.dispose()


def test_unverified_fertilizer_and_pesticide_sources_create_no_tasks():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(db)
            add_fertilizer_rule(
                db, active=False, verification_status="needs_review"
            )
            source = KnowledgeSource(
                title="Test pesticide guide",
                file_name="test.xlsx",
                verification_status="needs_review",
            )
            db.add(source)
            db.flush()
            db.add(
                AgriculturalSourceRecord(
                    source_id=source.id,
                    sheet_name="Pesticide - Diseases",
                    source_row=2,
                    crop_name="tomato",
                    problem_name="Test disease",
                    raw_data={
                        "Disease": "Test disease",
                        "Treatment": "Unverified test treatment",
                    },
                    verification_status="needs_review",
                    is_active=False,
                )
            )
            db.commit()

            assert generate_daily_monitoring_tasks(db, TARGET_DATE) == 1
            assert generate_daily_tasks(db, TARGET_DATE) == 0
            assert generate_irrigation_tasks(db, TARGET_DATE) == 0
            tasks = db.scalars(
                select(DailyTask).where(DailyTask.crop_cycle_id == cycle.id)
            ).all()
            assert len(tasks) == 1
            assert tasks[0].source_rule_type == "daily_monitoring"
    finally:
        engine.dispose()


def test_verified_active_fertilizer_creates_one_safe_reminder_without_duplicates():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(db)
            add_fertilizer_rule(
                db,
                active=True,
                verification_status="verified",
                fertilizer_name="19:19:19",
            )
            add_fertilizer_rule(
                db,
                active=True,
                verification_status="verified",
                fertilizer_name="Urea",
            )
            db.commit()

            assert generate_daily_tasks(db, TARGET_DATE) == 1
            assert generate_daily_tasks(db, TARGET_DATE) == 0
            tasks = db.scalars(
                select(DailyTask).where(DailyTask.crop_cycle_id == cycle.id)
            ).all()
            assert len(tasks) == 1
            assert "stage, not a dose" in tasks[0].description
            assert tasks[0].source_rule_type == "fertilizer_stage"
    finally:
        engine.dispose()


def test_fertilizer_task_is_not_generated_before_transplanting():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(db, planting_date=date(2026, 10, 15))
            add_fertilizer_rule(db, active=True, verification_status="verified")
            db.commit()
            assert generate_daily_tasks(db, TARGET_DATE) == 0
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id
                )
            ) == 0
    finally:
        engine.dispose()


def test_irrigation_requires_verified_active_rule_and_zero_rainfall():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            farm, cycle = create_crop_cycle(db)
            add_irrigation_rule(db)
            db.commit()

            # Missing weather is not interpreted as dry weather.
            assert generate_irrigation_tasks(db, TARGET_DATE) == 0
            db.add(
                WeatherRecord(
                    farm_id=farm.id,
                    observed_at=datetime(2026, 10, 14, 12),
                    rainfall_mm=0.1,
                )
            )
            db.commit()
            assert generate_irrigation_tasks(db, TARGET_DATE) == 0

            db.add(
                WeatherRecord(
                    farm_id=farm.id,
                    observed_at=datetime(2026, 10, 14, 18),
                    rainfall_mm=0,
                )
            )
            db.commit()
            assert generate_irrigation_tasks(db, TARGET_DATE) == 1
            assert generate_irrigation_tasks(db, TARGET_DATE) == 0
            task = db.scalar(
                select(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.source_rule_type == "irrigation",
                )
            )
            assert task is not None
            assert "not an instruction to apply a specific volume" in task.description
            assert task.weather_context["status"] == "observed"
            assert task.weather_context["rainfall_mm"] == 0
    finally:
        engine.dispose()


def test_irrigation_skips_ambiguous_constraints_and_unverified_rules():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            farm, _ = create_crop_cycle(db)
            add_irrigation_rule(
                db, active=True, verification_status="needs_review"
            )
            add_irrigation_rule(
                db,
                active=True,
                verification_status="verified",
                weather_constraints="Avoid irrigation before heavy rain",
            )
            db.add(
                WeatherRecord(
                    farm_id=farm.id,
                    observed_at=datetime(2026, 10, 14, 8),
                    rainfall_mm=0,
                )
            )
            db.commit()
            assert generate_irrigation_tasks(db, TARGET_DATE) == 0
    finally:
        engine.dispose()


def test_crop_stage_lookup_requires_one_verified_matching_rule():
    engine = setup_database()
    try:
        with Session(engine) as db:
            _, cycle = create_crop_cycle(db)
            db.add(
                CropStageRule(
                    crop_name="tomato",
                    stage_name="Establishment",
                    day_start=0,
                    day_end=9,
                    days_basis="after_transplanting",
                    verification_status="verified",
                )
            )
            db.commit()

            result = get_crop_stage(db, cycle.id, TARGET_DATE)
            assert result["stage_name"] == "Establishment"

            db.add(
                CropStageRule(
                    crop_name="tomato",
                    stage_name="Overlapping verified rule",
                    day_start=0,
                    day_end=9,
                    days_basis="after_transplanting",
                    verification_status="verified",
                )
            )
            db.commit()
            result = get_crop_stage(db, cycle.id, TARGET_DATE)
            assert result["stage_name"] is None
            assert "Multiple verified" in result["message"]

            before = get_crop_stage(db, cycle.id, date(2026, 10, 13))
            assert before["stage_name"] is None
            assert "before transplanting" in before["message"]
    finally:
        engine.dispose()


def test_verified_crop_stage_rule_still_generates_stage_milestone():
    engine = setup_database()
    try:
        with Session(engine, autoflush=False) as db:
            _, cycle = create_crop_cycle(db)
            db.add(
                CropStageRule(
                    crop_name="tomato",
                    stage_name="Establishment",
                    day_start=0,
                    day_end=9,
                    days_basis="after_transplanting",
                    verification_status="verified",
                )
            )
            db.commit()

            assert generate_stage_milestone_tasks(db, TARGET_DATE) == 1
            task = db.scalar(
                select(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle.id,
                    DailyTask.source_rule_type == "stage_milestone",
                )
            )
            assert task is not None
            assert "Establishment" in task.title
    finally:
        engine.dispose()


def test_missing_crop_cycle_is_reported():
    engine = setup_database()
    try:
        with Session(engine) as db:
            try:
                get_crop_stage(db, 999, TARGET_DATE)
            except ValueError as exc:
                assert str(exc) == "Crop cycle not found."
            else:
                raise AssertionError("Expected missing crop cycle to raise ValueError")
    finally:
        engine.dispose()


def test_task_api_routes_are_registered():
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/tasks" in paths
    assert "/api/v1/tasks/generate" in paths
    assert "/api/v1/tasks/crop-stage" in paths


def test_task_endpoints_require_auth_and_enforce_farmer_ownership():
    engine = setup_database()

    def override_get_db():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with Session(engine, autoflush=False) as db:
            farm_a, cycle_a = create_crop_cycle(db)
            farm_b, cycle_b = create_crop_cycle(db)
            farmer_a_id = farm_a.farmer_id
            farmer_b_id = farm_b.farmer_id

            db.add_all(
                [
                    DailyTask(
                        crop_cycle_id=cycle_a.id,
                        task_date=TARGET_DATE,
                        title="Farmer A task",
                        status="pending",
                        source_rule_type="test",
                    ),
                    DailyTask(
                        crop_cycle_id=cycle_b.id,
                        task_date=TARGET_DATE,
                        title="Farmer B task",
                        status="pending",
                        source_rule_type="test",
                    ),
                    FertilizerRule(
                        crop_name="tomato",
                        stage_name="Establishment",
                        day_start=0,
                        day_end=9,
                        days_basis="after_transplanting",
                        fertilizer_name="Test fertilizer",
                        frequency="once every 3 days",
                        application_method="fertigation",
                        verification_status="verified",
                        is_active=True,
                    ),
                ]
            )
            db.commit()
            cycle_a_id, cycle_b_id = cycle_a.id, cycle_b.id

        with TestClient(app) as client:
            assert client.get("/api/v1/tasks").status_code == 401
            assert (
                client.post(
                    f"/api/v1/tasks/generate?target_date={TARGET_DATE.isoformat()}"
                ).status_code
                == 401
            )
            assert (
                client.get(
                    "/api/v1/tasks/crop-stage",
                    params={
                        "crop_cycle_id": cycle_a_id,
                        "target_date": TARGET_DATE.isoformat(),
                    },
                ).status_code
                == 401
            )

            farmer_a_headers = {
                "Authorization": f"Bearer {create_access_token(farmer_a_id)}"
            }
            tasks = client.get("/api/v1/tasks", headers=farmer_a_headers).json()
            assert [task["title"] for task in tasks] == ["Farmer A task"]

            guessed_cycle = client.get(
                "/api/v1/tasks/crop-stage",
                params={
                    "crop_cycle_id": cycle_b_id,
                    "target_date": TARGET_DATE.isoformat(),
                },
                headers=farmer_a_headers,
            )
            assert guessed_cycle.status_code == 404
            assert guessed_cycle.json()["detail"] == "Crop cycle not found."

            generated = client.post(
                f"/api/v1/tasks/generate?target_date={TARGET_DATE.isoformat()}",
                headers=farmer_a_headers,
            )
            assert generated.status_code == 200
            assert generated.json()["tasks_created"] == 2
            assert generated.json()["message"].startswith(
                "Task generation completed. Daily crop monitoring: 1;"
            )
            listed_after_generation = client.get(
                "/api/v1/tasks",
                params={"task_date": TARGET_DATE.isoformat()},
                headers=farmer_a_headers,
            ).json()
            assert any(
                task["source_rule_type"] == "daily_monitoring"
                for task in listed_after_generation
            )

        with Session(engine) as db:
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle_a_id,
                    DailyTask.source_rule_type == "fertilizer_stage",
                )
            ) == 1
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle_a_id,
                    DailyTask.source_rule_type == "daily_monitoring",
                )
            ) == 1
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle_b_id,
                    DailyTask.source_rule_type == "fertilizer_stage",
                )
            ) == 0
            assert db.scalar(
                select(func.count()).select_from(DailyTask).where(
                    DailyTask.crop_cycle_id == cycle_b_id,
                    DailyTask.source_rule_type == "daily_monitoring",
                )
            ) == 0
            assert farmer_a_id != farmer_b_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
