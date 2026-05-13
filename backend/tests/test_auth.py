"""
Тесты авторизации, управления пользователями и безопасности.

Покрывает:
- POST /auth/login
- GET  /auth/me
- POST /auth/logout
- POST /auth/register
- POST /auth/users
- GET  /auth/users
- PATCH /auth/users/{id}
- PATCH /auth/users/{id}/reset-password
- PATCH /auth/me/change-password
- Rate limiting на login
- Token version invalidation
- Password strength validation
"""
import pytest
from tests.conftest import _make_user
from models.user import UserRole


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success(client, user_omts):
    resp = client.post("/auth/login", data={"username": "omts_test", "password": "testpass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_login_wrong_password(client, user_omts):
    resp = client.post("/auth/login", data={"username": "omts_test", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/auth/login", data={"username": "nobody", "password": "doesntmatter"})
    assert resp.status_code == 401


def test_login_inactive_user_blocked(client, db, user_omts):
    """Деактивированный пользователь не может использовать токен."""
    user_omts.is_active = False
    db.flush()
    resp = client.post("/auth/login", data={"username": "omts_test", "password": "testpass123"})
    token = resp.json().get("access_token")
    resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 401


def test_login_rate_limit(client, user_omts):
    """После 10 неудачных попыток с одного IP — 429."""
    for _ in range(10):
        client.post("/auth/login", data={"username": "omts_test", "password": "badpassword"})
    resp = client.post("/auth/login", data={"username": "omts_test", "password": "badpassword"})
    assert resp.status_code == 429


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

def test_me_authenticated(client, headers_omts):
    resp = client.get("/auth/me", headers=headers_omts)
    assert resp.status_code == 200
    assert resp.json()["username"] == "omts_test"


def test_me_no_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /auth/logout + token_version invalidation
# ---------------------------------------------------------------------------

def test_logout_invalidates_token(client, user_omts):
    """После logout старый токен должен быть отклонён."""
    login = client.post("/auth/login", data={"username": "omts_test", "password": "testpass123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Токен работает до logout
    assert client.get("/auth/me", headers=headers).status_code == 200

    # Logout
    assert client.post("/auth/logout", headers=headers).status_code == 200

    # Старый токен больше не работает
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 401


def test_logout_requires_auth(client):
    resp = client.post("/auth/logout")
    assert resp.status_code == 401


def test_new_token_works_after_logout(client, user_omts):
    """После logout можно снова войти и получить рабочий токен."""
    h = {"Authorization": f"Bearer {client.post('/auth/login', data={'username': 'omts_test', 'password': 'testpass123'}).json()['access_token']}"}
    client.post("/auth/logout", headers=h)

    new_login = client.post("/auth/login", data={"username": "omts_test", "password": "testpass123"})
    new_token = new_login.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /auth/register
# ---------------------------------------------------------------------------

def test_register_disabled_by_default(client):
    """REGISTER_ENABLED=false — регистрация возвращает 403."""
    resp = client.post("/auth/register", json={
        "username": "selfreguser",
        "full_name": "Self Reg",
        "department": "ОМТС",
        "password": "securepass1",
    })
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /auth/users
# ---------------------------------------------------------------------------

def test_list_users_admin(client, headers_admin, user_omts):
    resp = client.get("/auth/users", headers=headers_admin)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "omts_test" in usernames


def test_list_users_omts_allowed(client, headers_omts):
    """ОМТС может просматривать список пользователей."""
    resp = client.get("/auth/users", headers=headers_omts)
    assert resp.status_code == 200


def test_list_users_workshop_forbidden(client, headers_workshop):
    resp = client.get("/auth/users", headers=headers_workshop)
    assert resp.status_code == 403


def test_list_users_quality_forbidden(client, headers_quality):
    resp = client.get("/auth/users", headers=headers_quality)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /auth/users — создание пользователя
# ---------------------------------------------------------------------------

def test_create_user_by_admin(client, headers_admin):
    resp = client.post("/auth/users", json={
        "username": "newuser2",
        "full_name": "New User",
        "role": "planning",
        "password": "securepass1",
    }, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["username"] == "newuser2"


def test_create_user_requires_admin(client, headers_omts):
    """ОМТС не может создавать пользователей."""
    resp = client.post("/auth/users", json={
        "username": "newuser3",
        "full_name": "New",
        "role": "planning",
        "password": "securepass1",
    }, headers=headers_omts)
    assert resp.status_code == 403


def test_create_user_duplicate_username(client, headers_admin, user_omts):
    resp = client.post("/auth/users", json={
        "username": "omts_test",
        "full_name": "Duplicate",
        "role": "omts",
        "password": "securepass1",
    }, headers=headers_admin)
    assert resp.status_code == 400


def test_create_user_password_too_short(client, headers_admin):
    """Пароль короче 8 символов — 422 Unprocessable Entity."""
    resp = client.post("/auth/users", json={
        "username": "shortpwd",
        "full_name": "Short Pwd",
        "role": "planning",
        "password": "1234567",
    }, headers=headers_admin)
    assert resp.status_code == 422


def test_create_user_password_exactly_8(client, headers_admin):
    """Ровно 8 символов — должен пройти."""
    resp = client.post("/auth/users", json={
        "username": "pwd8chars",
        "full_name": "Pwd 8",
        "role": "planning",
        "password": "12345678",
    }, headers=headers_admin)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# PATCH /auth/users/{id} — редактирование
# ---------------------------------------------------------------------------

def test_update_user_role(client, headers_admin, db, user_omts):
    resp = client.patch(f"/auth/users/{user_omts.id}", json={"role": "planning"}, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["role"] == "planning"
    db.refresh(user_omts)
    assert user_omts.role == UserRole.planning


def test_update_user_deactivate(client, headers_admin, db, user_omts):
    resp = client.patch(f"/auth/users/{user_omts.id}", json={"is_active": False}, headers=headers_admin)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    db.refresh(user_omts)
    assert user_omts.is_active is False


def test_update_user_cannot_deactivate_self(client, headers_admin, user_admin):
    """Администратор не может деактивировать сам себя."""
    resp = client.patch(f"/auth/users/{user_admin.id}", json={"is_active": False}, headers=headers_admin)
    assert resp.status_code == 400


def test_update_user_requires_admin(client, headers_omts, user_workshop):
    resp = client.patch(f"/auth/users/{user_workshop.id}", json={"role": "planning"}, headers=headers_omts)
    assert resp.status_code == 403


def test_update_nonexistent_user(client, headers_admin):
    resp = client.patch("/auth/users/99999", json={"role": "planning"}, headers=headers_admin)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /auth/users/{id}/reset-password
# ---------------------------------------------------------------------------

def test_reset_password_by_admin(client, headers_admin, user_omts):
    resp = client.patch(f"/auth/users/{user_omts.id}/reset-password",
                        json={"new_password": "newpassword99"},
                        headers=headers_admin)
    assert resp.status_code == 200
    # Проверяем что новый пароль работает
    login = client.post("/auth/login", data={"username": "omts_test", "password": "newpassword99"})
    assert login.status_code == 200


def test_reset_password_requires_admin(client, headers_omts, user_workshop):
    resp = client.patch(f"/auth/users/{user_workshop.id}/reset-password",
                        json={"new_password": "newpassword99"},
                        headers=headers_omts)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /auth/me/change-password
# ---------------------------------------------------------------------------

def test_change_own_password(client, user_omts):
    headers = {"Authorization": f"Bearer {client.post('/auth/login', data={'username': 'omts_test', 'password': 'testpass123'}).json()['access_token']}"}
    resp = client.patch("/auth/me/change-password",
                        json={"old_password": "testpass123", "new_password": "changed12345"},
                        headers=headers)
    assert resp.status_code == 200
    # Старый пароль больше не работает
    assert client.post("/auth/login", data={"username": "omts_test", "password": "testpass123"}).status_code == 401
    # Новый работает
    assert client.post("/auth/login", data={"username": "omts_test", "password": "changed12345"}).status_code == 200


def test_change_own_password_wrong_old(client, headers_omts):
    resp = client.patch("/auth/me/change-password",
                        json={"old_password": "wrongoldpassword", "new_password": "newpassword99"},
                        headers=headers_omts)
    assert resp.status_code == 400
