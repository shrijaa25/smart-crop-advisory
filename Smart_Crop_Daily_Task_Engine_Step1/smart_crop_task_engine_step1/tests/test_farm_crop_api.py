from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import CropStageRule, Farm, Farmer


def test_farm_and_crop_routes_enforce_authenticated_ownership():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine, autoflush=False) as db:
        farmer_a = Farmer(full_name="Farmer A", phone="9000000101")
        farmer_b = Farmer(full_name="Farmer B", phone="9000000102")
        db.add_all([farmer_a, farmer_b])
        db.commit()
        farmer_a_id, farmer_b_id = farmer_a.id, farmer_b.id

    def override_get_db():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            headers_a = {"Authorization": f"Bearer {create_access_token(farmer_a_id)}"}
            headers_b = {"Authorization": f"Bearer {create_access_token(farmer_b_id)}"}

            assert client.get("/api/v1/farms").status_code == 401
            assert client.get("/api/v1/crop-cycles").status_code == 401

            farm_response = client.post(
                "/api/v1/farms",
                headers=headers_a,
                json={
                    "name": "North field",
                    "village": "Test village",
                    "district": "Test district",
                    "state": "Maharashtra",
                    "area_value": 2.5,
                    "area_unit": "acre",
                    "soil_type": "loam",
                    "irrigation_method": "drip",
                    "latitude": 19.1,
                    "longitude": 72.9,
                    # Extra browser-supplied owner data is ignored.
                    "farmer_id": farmer_b_id,
                },
            )
            assert farm_response.status_code == 201, farm_response.text
            farm_id = farm_response.json()["id"]

            optional_area_farm = client.post(
                "/api/v1/farms",
                headers=headers_a,
                json={"name": "Area not recorded"},
            )
            assert optional_area_farm.status_code == 201, optional_area_farm.text
            assert optional_area_farm.json()["area_value"] is None

            missing_crop_area = client.post(
                f"/api/v1/farms/{farm_id}/crops",
                headers=headers_a,
                json={
                    "crop_name": "tomato",
                    "planting_date": "2026-10-01",
                    "area_unit": "acre",
                },
            )
            assert missing_crop_area.status_code == 422

            zero_crop_area = client.post(
                f"/api/v1/farms/{farm_id}/crops",
                headers=headers_a,
                json={
                    "crop_name": "tomato",
                    "planting_date": "2026-10-01",
                    "area_value": 0,
                    "area_unit": "acre",
                },
            )
            assert zero_crop_area.status_code == 422

            with Session(engine) as db:
                farm = db.scalar(select(Farm).where(Farm.id == farm_id))
                assert farm is not None and farm.farmer_id == farmer_a_id

            assert [farm["id"] for farm in client.get("/api/v1/farms", headers=headers_a).json()] == [
                farm_id,
                optional_area_farm.json()["id"],
            ]
            assert client.get("/api/v1/farms", headers=headers_b).json() == []

            crop_response = client.post(
                f"/api/v1/farms/{farm_id}/crops",
                headers=headers_a,
                json={
                    "crop_name": "tomato",
                    "variety": "Hybrid test",
                    "planting_date": "2026-10-01",
                    "planting_method": "transplanting",
                    "area_value": 1.25,
                    "area_unit": "acre",
                },
            )
            assert crop_response.status_code == 201, crop_response.text
            crop_cycle_id = crop_response.json()["id"]

            assert len(client.get("/api/v1/crop-cycles", headers=headers_a).json()) == 1
            assert client.get("/api/v1/crop-cycles", headers=headers_b).json() == []
            assert client.get(
                f"/api/v1/farms/{farm_id}/crops", headers=headers_b
            ).status_code == 404
            assert client.post(
                f"/api/v1/farms/{farm_id}/crops",
                headers=headers_b,
                json={
                    "crop_name": "chilli",
                    "planting_date": "2026-10-01",
                    "area_value": 1,
                    "area_unit": "acre",
                },
            ).status_code == 404

            stage = client.get(
                "/api/v1/tasks/crop-stage",
                params={"crop_cycle_id": crop_cycle_id, "target_date": "2026-10-14"},
                headers=headers_a,
            )
            assert stage.status_code == 200
            assert stage.json()["crop_age_days"] == 13
            assert stage.json()["stage_name"] is None
            assert stage.json()["message"] == "No verified crop-stage rule matches this crop age."

            assert client.get(
                "/api/v1/tasks/crop-stage",
                params={"crop_cycle_id": crop_cycle_id, "target_date": "2026-10-14"},
                headers=headers_b,
            ).status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_verified_stage_is_returned_for_owned_crop():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine, autoflush=False) as db:
        farmer = Farmer(full_name="Stage Farmer", phone="9000000103")
        db.add(farmer)
        db.flush()
        farm = Farm(farmer_id=farmer.id, name="Stage Farm")
        db.add(farm)
        db.flush()
        from app.models import CropCycle

        cycle = CropCycle(
            farm_id=farm.id,
            crop_name="chilli",
            planting_date=date(2026, 10, 1),
            planting_method="transplanting",
            area_value=1,
            area_unit="acre",
            status="active",
        )
        db.add(cycle)
        db.flush()
        db.add(
            CropStageRule(
                crop_name="chilli",
                stage_name="Verified establishment stage",
                day_start=0,
                day_end=20,
                days_basis="after_transplanting",
                verification_status="verified",
            )
        )
        db.commit()
        farmer_id, cycle_id = farmer.id, cycle.id

    def override_get_db():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/tasks/crop-stage",
                params={"crop_cycle_id": cycle_id, "target_date": "2026-10-14"},
                headers={"Authorization": f"Bearer {create_access_token(farmer_id)}"},
            )
            assert response.status_code == 200
            assert response.json()["crop_age_days"] == 13
            assert response.json()["stage_name"] == "Verified establishment stage"
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()
