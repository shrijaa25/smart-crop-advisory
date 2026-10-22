import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_knowledge_summary(client):
    response = client.get("/api/v1/knowledge/summary")
    assert response.status_code == 200
    assert response.json()["supported_crops"] == ["tomato", "chilli"]


def test_reject_unsupported_crop(client):
    response = client.get("/api/v1/knowledge/fertilizer-rules?crop=brinjal")
    assert response.status_code == 400
