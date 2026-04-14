from fastapi import status
from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "healthy"
    assert "version" in body


def test_health_check_has_correlation_id():
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_custom_correlation_id_echoed():
    response = client.get("/health", headers={"X-Request-ID": "my-trace-123"})
    assert response.headers["x-request-id"] == "my-trace-123"
