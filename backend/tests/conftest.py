import pytest

from app.services.auth import auth_service


@pytest.fixture(autouse=True)
def isolated_auth_db(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_service.settings, "database_url", None)
    monkeypatch.setattr(auth_service, "db_path", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(auth_service.settings, "auth_token_ttl_days", 30)
    monkeypatch.setattr(auth_service.settings, "daily_query_limit", 50)
    monkeypatch.setattr(auth_service.settings, "owner_email", "owner@example.com")
    monkeypatch.setattr(auth_service.settings, "owner_password", "ownerpass123")
    monkeypatch.setattr(auth_service.settings, "owner_full_name", "Project Owner")
    auth_service.initialize()


@pytest.fixture
def approved_auth_headers():
    auth_service.create_user(
        email="approved@example.com",
        password="strongpass1",
        full_name="Approved User",
        access_reason="Testing GPT explanation access.",
    )
    token, _ = auth_service.authenticate_user(email="approved@example.com", password="strongpass1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_auth_headers():
    token, _ = auth_service.authenticate_user(email="owner@example.com", password="ownerpass123")
    return {"Authorization": f"Bearer {token}"}
