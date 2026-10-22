from datetime import date
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import CropCycle, DailyTask, Farm, Farmer, FarmerObservation, TaskHistory
from app.services.weather import get_weather
import app.services.weather as weather_service


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine


def test_weather_without_coordinates_is_explicitly_unavailable():
    result = asyncio.run(get_weather(None, None))
    assert result["status"] == "unavailable"
    assert "coordinates" in result["reason"]


def test_weather_api_failure_is_explicitly_unavailable(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, *args, **kwargs):
            import httpx
            raise httpx.ConnectError("offline")
    monkeypatch.setattr(weather_service.httpx, "AsyncClient", FailingClient)
    result = asyncio.run(get_weather(10, 20))
    assert result["status"] == "unavailable"
    assert "Weather service unavailable" in result["reason"]


def test_activity_endpoints_preserve_status_history_and_observations():
    engine = _db()

    def override_db():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with Session(engine) as db:
            farmer = Farmer(full_name="Activity Farmer")
            db.add(farmer)
            db.flush()
            farm = Farm(farmer_id=farmer.id, name="Farm")
            db.add(farm)
            db.flush()
            cycle = CropCycle(farm_id=farm.id, crop_name="tomato", planting_date=date(2026, 1, 1))
            db.add(cycle)
            db.flush()
            task = DailyTask(crop_cycle_id=cycle.id, task_date=date(2026, 1, 2), title="Inspect", status="pending")
            db.add(task)
            db.commit()
            farmer_id, cycle_id, task_id = farmer.id, cycle.id, task.id

        headers = {"Authorization": f"Bearer {create_access_token(farmer_id)}"}
        with TestClient(app) as client:
            updated = client.patch(f"/api/v1/tasks/{task_id}/status", headers=headers, json={"status": "completed", "notes": "done"})
            assert updated.status_code == 200
            assert updated.json()["completed_at"] is not None
            obs = client.post("/api/v1/tasks/observations", headers=headers, json={"crop_cycle_id": cycle_id, "task_id": task_id, "note": "Leaf discoloration", "photo_reference": "farm/photo-1.jpg"})
            assert obs.status_code == 201
            listed = client.get(f"/api/v1/tasks/observations?crop_cycle_id={cycle_id}", headers=headers)
            assert listed.status_code == 200
            assert listed.json()[0]["note"] == "Leaf discoloration"
            moved = client.patch(f"/api/v1/tasks/{task_id}/status", headers=headers, json={"status": "rescheduled", "new_due_date": "2026-01-05"})
            assert moved.status_code == 200
            assert moved.json()["task_date"] == "2026-01-05"
            assert moved.json()["completed_at"] is None
            assert client.patch(f"/api/v1/tasks/{task_id}/status", headers=headers, json={"status": "invalid"}).status_code == 422
            history = client.get(f"/api/v1/tasks/{task_id}/history", headers=headers)
            assert [entry["action"] for entry in history.json()] == ["completed", "rescheduled"]
        with Session(engine) as db:
            assert db.scalar(select(TaskHistory).where(TaskHistory.task_id == task_id)).action == "completed"
            assert db.scalar(select(FarmerObservation).where(FarmerObservation.crop_cycle_id == cycle_id)) is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_farmer_created_fertilizer_rules_stay_inactive_and_pending():
    engine = _db()
    def override_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    try:
        with Session(engine) as db:
            farmer = Farmer(full_name="Knowledge Farmer")
            db.add(farmer)
            db.commit()
            farmer_id = farmer.id
        headers = {"Authorization": f"Bearer {create_access_token(farmer_id)}"}
        payload = {
            "crop_name": "chilli", "fertilizer_name": "Test", "verification_status": "verified", "is_active": True
        }
        with TestClient(app) as client:
            response = client.post("/api/v1/knowledge/fertilizer-rules", headers=headers, json=payload)
        assert response.status_code == 201
        assert response.json()["verification_status"] == "needs_review"
        assert response.json()["is_active"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_disease_model_status_does_not_claim_predictions():
    with TestClient(app) as client:
        response = client.get("/api/v1/tasks/disease-detection/status")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["model_version"] is None
