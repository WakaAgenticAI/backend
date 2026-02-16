import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
# Raise rate limits for test suite (default 100/60s is too low for 300+ tests)
os.environ.setdefault("MAX_LOGIN_ATTEMPTS", "500")
os.environ.setdefault("LOGIN_LOCKOUT_MINUTES", "1")

# Ensure the backend package root is importable when running tests directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.users import User  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.core.middleware import SimpleRateLimitMiddleware, LoginRateLimitMiddleware  # noqa: E402

TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin123"


def _ensure_test_user():
    """Seed a test user if not already present."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == TEST_EMAIL).first()
        if not existing:
            user = User(
                email=TEST_EMAIL,
                password_hash=get_password_hash(TEST_PASSWORD),
                full_name="Test Admin",
                status="active",
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


_ensure_test_user()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict:
    """Return Authorization headers with a valid access token."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Clear rate limiter buckets before each test to prevent 429 cascading."""
    SimpleRateLimitMiddleware.buckets.clear()
    LoginRateLimitMiddleware._attempts.clear()


@pytest.fixture
def db_session():
    """Provide a transactional DB session that rolls back after each test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
