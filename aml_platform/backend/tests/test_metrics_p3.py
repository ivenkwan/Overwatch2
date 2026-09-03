"""TASK-022: /metrics endpoint and counters."""

from fastapi.testclient import TestClient

from app.core.config import AUTH_MODE_LOCAL, get_settings
from app.main import app


def test_metrics_endpoint_counts_requests(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", AUTH_MODE_LOCAL)
    monkeypatch.setenv("JWT_SECRET_KEY", "s" * 48)
    get_settings.cache_clear()
    client = TestClient(app)
    # a 401 (no auth) and the health 200 both get counted
    client.get("/api/v1/alerts/feed")
    client.get("/health")
    body = client.get("/metrics").text
    assert "aml_http_requests_total" in body
    assert 'route="/health"' in body or 'route="/api/v1/alerts/feed"' in body
    assert 'status="401"' in body
    assert "aml_http_request_duration_seconds" in body
    get_settings.cache_clear()
