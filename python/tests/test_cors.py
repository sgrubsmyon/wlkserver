from fastapi.testclient import TestClient

from python.main import app


def test_cors_allows_dev_origin():
    with TestClient(app) as c:
        r = c.get("/", headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_for_unknown_origin():
    with TestClient(app) as c:
        r = c.options(
            "/verkauf/",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in r.headers


def test_cors_preflight_allows_post():
    with TestClient(app) as c:
        r = c.options(
            "/verkauf/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "POST" in r.headers["access-control-allow-methods"]
