import pytest
from fastapi.testclient import TestClient

from api.config import get_settings
from api.main import app

# follow_redirects=False, or the client chases the 301 to a host that does not
# exist and the assertion under test never runs.
client = TestClient(app, follow_redirects=False)


@pytest.fixture
def in_production(monkeypatch):
    """Settings are cached per process, so the cache has to go both ways."""
    monkeypatch.setenv("EDUBOT_ENVIRONMENT", "production")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_plain_http_is_redirected_in_production(in_production):
    response = client.get("/health", headers={"X-Forwarded-Proto": "http"})

    assert response.status_code == 301
    assert response.headers["location"] == "https://testserver/health"


def test_the_path_and_query_survive_the_redirect(in_production):
    response = client.get("/health?verbose=1", headers={"X-Forwarded-Proto": "http"})

    assert response.headers["location"] == "https://testserver/health?verbose=1"


def test_https_is_served_with_hsts(in_production):
    response = client.get("/health", headers={"X-Forwarded-Proto": "https"})

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=2592000"


def test_local_development_is_left_alone():
    """Nobody runs a certificate on their laptop, so the rule is production-only."""
    response = client.get("/health", headers={"X-Forwarded-Proto": "http"})

    assert response.status_code == 200
    assert "strict-transport-security" not in response.headers
