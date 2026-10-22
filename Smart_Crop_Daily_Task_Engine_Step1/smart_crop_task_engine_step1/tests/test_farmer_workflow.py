from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import CropCycle, DailyTask, Farm, Farmer, FertilizerRule

TARGET_DATE = date(2026, 10, 14)


def test_farmer_setup_and_safe_task_engine_workflow(tmp_path):
    database_path = (tmp_path / "workflow.db").as_posix()
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            register = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Workflow Farmer",
                    "phone": "9000000201",
                    "password": "SafeTest@2026",
                    "preferred_language": "en",
                },
            )
            assert register.status_code == 201, register.text
            farmer_id = register.json()["id"]
            assert "password" not in register.json()
            assert "password_hash" not in register.json()
            # Account registration has no farm/crop area field; area is
            # collected on farm/crop records during setup instead.
            assert "area_value" not in register.json()
            assert "crop_area" not in register.json()
            assert client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Workflow Farmer",
                    "phone": "9000000201",
                    "password": "SafeTest@2026",
                    "preferred_language": "en",
                },
            ).status_code == 409
            assert client.post(
                "/api/v1/auth/login",
                data={"username": "9000000201", "password": "incorrect"},
            ).status_code == 401

            login = client.post(
                "/api/v1/auth/login",
                data={"username": "9000000201", "password": "SafeTest@2026"},
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            profile = client.get("/api/v1/auth/me", headers=headers)
            assert profile.status_code == 200
            assert profile.json()["id"] == farmer_id
            assert "area_value" not in profile.json()

            farm_response = client.post(
                "/api/v1/farms",
                headers=headers,
                json={
                    "name": "Workflow Farm",
                    "village": "Test village",
                    "district": "Test district",
                    "state": "Maharashtra",
                    "area_value": 2,
                    "area_unit": "acre",
                    "soil_type": "loam",
                    "irrigation_method": "drip",
                },
            )
            assert farm_response.status_code == 201, farm_response.text
            farm_id = farm_response.json()["id"]

            future_crop = client.post(
                f"/api/v1/farms/{farm_id}/crops",
                headers=headers,
                json={
                    "crop_name": "tomato",
                    "planting_date": "2099-01-01",
                    "area_value": 1,
                    "area_unit": "acre",
                },
            )
            assert future_crop.status_code == 422

            crop_ids = {}
            for crop_name in ("tomato", "chilli"):
                response = client.post(
                    f"/api/v1/farms/{farm_id}/crops",
                    headers=headers,
                    json={
                        "crop_name": crop_name,
                        "variety": f"{crop_name.title()} test variety",
                        "planting_date": TARGET_DATE.isoformat(),
                        "planting_method": "transplanting",
                        "area_value": 0.5,
                        "area_unit": "acre",
                    },
                )
                assert response.status_code == 201, response.text
                crop_ids[crop_name] = response.json()["id"]

            with Session(engine) as db:
                assert db.scalar(select(func.count()).select_from(Farm).where(Farm.farmer_id == farmer_id)) == 1
                assert db.scalar(
                    select(func.count())
                    .select_from(CropCycle)
                    .join(Farm, CropCycle.farm_id == Farm.id)
                    .where(Farm.farmer_id == farmer_id)
                ) == 2
                # An imported needs_review rule stays ineligible.
                db.add(
                    FertilizerRule(
                        crop_name="tomato",
                        stage_name="Review pending stage",
                        day_start=0,
                        day_end=9,
                        days_basis="after_transplanting",
                        fertilizer_name="Review-pending fertilizer",
                        frequency="once every 3 days",
                        application_method="fertigation",
                        verification_status="needs_review",
                        is_active=False,
                    )
                )
                db.commit()

            for crop_name, crop_id in crop_ids.items():
                stage = client.get(
                    "/api/v1/tasks/crop-stage",
                    params={"crop_cycle_id": crop_id, "target_date": TARGET_DATE.isoformat()},
                    headers=headers,
                )
                assert stage.status_code == 200
                assert stage.json()["crop_name"] == crop_name
                assert stage.json()["crop_age_days"] == 0
                assert stage.json()["stage_name"] is None

            unverified_run = client.post(
                "/api/v1/tasks/generate",
                params={"target_date": TARGET_DATE.isoformat()},
                headers=headers,
            )
            assert unverified_run.status_code == 200
            assert unverified_run.json()["tasks_created"] == 2
            initial_tasks = client.get(
                "/api/v1/tasks",
                params={"task_date": TARGET_DATE.isoformat()},
                headers=headers,
            ).json()
            assert len(initial_tasks) == 2
            assert all(task["source_rule_type"] == "daily_monitoring" for task in initial_tasks)

            with Session(engine) as db:
                db.add(
                    FertilizerRule(
                        crop_name="tomato",
                        stage_name="Verified establishment",
                        day_start=0,
                        day_end=9,
                        days_basis="after_transplanting",
                        fertilizer_name="Fixture verified rule",
                        frequency="once every 3 days",
                        application_method="fertigation",
                        verification_status="verified",
                        is_active=True,
                    )
                )
                db.commit()

            eligible_run = client.post(
                "/api/v1/tasks/generate",
                params={"target_date": TARGET_DATE.isoformat()},
                headers=headers,
            )
            assert eligible_run.status_code == 200
            assert eligible_run.json()["tasks_created"] == 1
            repeated_run = client.post(
                "/api/v1/tasks/generate",
                params={"target_date": TARGET_DATE.isoformat()},
                headers=headers,
            )
            assert repeated_run.status_code == 200
            assert repeated_run.json()["tasks_created"] == 0

            tasks = client.get(
                "/api/v1/tasks",
                params={"task_date": TARGET_DATE.isoformat()},
                headers=headers,
            ).json()
            assert len(tasks) == 3
            assert sum(task["source_rule_type"] == "daily_monitoring" for task in tasks) == 2
            assert any(task["crop_cycle_id"] == crop_ids["tomato"] for task in tasks)

            second_farmer = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Other Farmer",
                    "phone": "9000000202",
                    "password": "SafeTest@2026",
                    "preferred_language": "en",
                },
            )
            assert second_farmer.status_code == 201
            second_login = client.post(
                "/api/v1/auth/login",
                data={"username": "9000000202", "password": "SafeTest@2026"},
            )
            second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
            assert client.get("/api/v1/farms", headers=second_headers).json() == []
            assert client.get("/api/v1/crop-cycles", headers=second_headers).json() == []
            assert client.get(
                f"/api/v1/farms/{farm_id}/crops", headers=second_headers
            ).status_code == 404
            assert client.get(
                "/api/v1/tasks",
                params={"task_date": TARGET_DATE.isoformat()},
                headers=second_headers,
            ).json() == []
            assert client.get(
                "/api/v1/tasks/crop-stage",
                params={"crop_cycle_id": crop_ids["tomato"], "target_date": TARGET_DATE.isoformat()},
                headers=second_headers,
            ).status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
