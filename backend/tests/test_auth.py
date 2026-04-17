from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import auth_service


client = TestClient(app)


def test_sign_up_creates_approved_account() -> None:
    response = client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "member@example.com",
            "password": "strongpass1",
            "full_name": "Member User",
            "access_reason": "Need access for evaluation.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["email"] == "member@example.com"
    assert payload["user"]["status"] == "approved"
    assert payload["user"]["role"] == "member"
    assert "sign in immediately" in payload["message"].lower()


def test_new_account_can_sign_in_immediately() -> None:
    client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "member@example.com",
            "password": "strongpass1",
        },
    )

    response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "member@example.com",
            "password": "strongpass1",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["status"] == "approved"


def test_owner_account_is_bootstrapped_and_can_sign_in() -> None:
    response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "owner@example.com",
            "password": "ownerpass123",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["status"] == "approved"
    assert payload["user"]["role"] == "owner"


def test_owner_password_updates_when_environment_changes(monkeypatch) -> None:
    monkeypatch.setattr(auth_service.settings, "owner_password", "newownerpass456")
    auth_service.initialize()

    old_password_response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "owner@example.com",
            "password": "ownerpass123",
        },
    )
    assert old_password_response.status_code == 401

    new_password_response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "owner@example.com",
            "password": "newownerpass456",
        },
    )
    assert new_password_response.status_code == 200
    assert new_password_response.json()["user"]["role"] == "owner"


def test_owner_can_approve_and_user_can_sign_in(owner_auth_headers) -> None:
    client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "approved@example.com",
            "password": "strongpass1",
        },
    )

    approval_response = client.post(
        "/api/v1/auth/admin/approve",
        headers=owner_auth_headers,
        json={"email": "approved@example.com"},
    )

    assert approval_response.status_code == 200
    assert approval_response.json()["user"]["status"] == "approved"

    sign_in_response = client.post(
        "/api/v1/auth/sign-in",
        json={
            "email": "approved@example.com",
            "password": "strongpass1",
        },
    )

    assert sign_in_response.status_code == 200
    token = sign_in_response.json()["token"]
    assert token

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "approved@example.com"


def test_member_cannot_access_admin_routes(approved_auth_headers) -> None:
    response = client.get(
        "/api/v1/auth/admin/users?status=pending",
        headers=approved_auth_headers,
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access is required."}


def test_owner_can_list_approved_users(owner_auth_headers) -> None:
    client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "member@example.com",
            "password": "strongpass1",
        },
    )
    client.post(
        "/api/v1/auth/sign-up",
        json={
            "email": "other@example.com",
            "password": "strongpass1",
        },
    )

    response = client.get(
        "/api/v1/auth/admin/users?status=approved",
        headers=owner_auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert all(user["status"] == "approved" for user in payload)
