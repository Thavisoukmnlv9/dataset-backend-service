"""Smoke tests: verify the FastAPI app boots, core routes respond, and key modules import."""


# ── Core routes ──────────────────────────────────────────────────────────────

def test_root_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert "message" in body
    assert "version" in body


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "timestamp" in body


def test_api_v1_health_returns_200(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"


# ── Security headers ────────────────────────────────────────────────────────

def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"


def test_request_id_header(client):
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID") is not None


# ── Auth routes registered ───────────────────────────────────────────────────

def test_auth_login_route_exists(client):
    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code != 404, "Auth login route should be registered"


def test_auth_register_route_exists(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "a@b.com", "password": "TestPass1",
        "first_name": "A", "last_name": "B",
    })
    assert resp.status_code != 404, "Auth register route should be registered"


# ── User routes registered ───────────────────────────────────────────────────

def test_users_list_route_exists(client):
    resp = client.get("/api/v1/users")
    assert resp.status_code != 404, "Users list route should be registered"


def test_users_stats_route_exists(client):
    resp = client.get("/api/v1/users/stats")
    assert resp.status_code != 404, "Users stats route should be registered"


# ── Module imports ───────────────────────────────────────────────────────────

def test_core_modules_importable(_mock_prisma):
    """Verify key modules import without errors after cleanup."""
    import app.core.config
    import app.core.settings
    import app.core.security
    import app.core.middleware
    import app.core.urls
    import app.core.redis_client
    import app.shared.utils
    import app.shared.exceptions


def test_auth_route_module_importable(_mock_prisma):
    """Verify the newly created auth routes module imports cleanly."""
    import app.modules.auth.api.routes


def test_users_route_module_importable(_mock_prisma):
    """Verify the newly created users routes module imports cleanly."""
    import app.modules.users.api.routes
