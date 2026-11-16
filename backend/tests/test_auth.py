from sqlalchemy import text

from database import SessionLocal

CUSTOMER = {"full_name": "Abena Test", "email": "Abena@Example.com", "password": "Passw0rdOK", "phone": "0241234567"}


def register(client, **overrides):
    return client.post("/api/auth/register", json={**CUSTOMER, **overrides})


def test_register_customer_and_password_is_hashed(client):
    r = register(client)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["email"] == "abena@example.com"        # lower-cased
    assert body["user"]["role"] == "customer"
    assert "password" not in str(body)
    with SessionLocal() as db:
        stored = db.execute(text("select password_hash, phone from users")).one()
    assert stored[0].startswith("$2") and "Passw0rdOK" not in stored[0]
    assert stored[1] == "233241234567"                          # normalised for WhatsApp


def test_duplicate_email_rejected(client):
    register(client)
    assert register(client, email="abena@example.com").status_code == 409


def test_weak_password_and_bad_phone_rejected(client):
    assert register(client, password="short1").status_code == 422
    assert register(client, password="onlyletters").status_code == 422
    assert register(client, email="x@example.com", phone="12345").status_code == 422


def test_cannot_self_register_as_admin(client):
    assert register(client, role="admin").status_code == 422


def test_artisan_registration_creates_profile(client):
    r = register(client, email="k@example.com", role="artisan", category_id=1, location="madina")
    assert r.status_code == 201, r.text
    assert r.json()["user"]["artisan_profile"]["category_id"] == 1
    assert register(client, email="z@example.com", role="artisan").status_code == 422          # no category
    assert register(client, email="y@example.com", role="artisan", category_id=99).status_code == 422


def test_login_me_and_wrong_password(client):
    register(client)
    ok = client.post("/api/auth/login", json={"email": "ABENA@example.com", "password": "Passw0rdOK"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["full_name"] == "Abena Test"
    bad = client.post("/api/auth/login", json={"email": "abena@example.com", "password": "wrong-pass1"})
    assert bad.status_code == 401
    ghost = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Passw0rdOK"})
    assert ghost.status_code == 401 and ghost.json() == bad.json()   # no user enumeration


def test_protected_route_needs_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_login_rate_limit(client):
    register(client)
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "abena@example.com", "password": "nope-nope1"})
    r = client.post("/api/auth/login", json={"email": "abena@example.com", "password": "Passw0rdOK"})
    assert r.status_code == 429


def test_suspended_user_blocked(client):
    token = register(client).json()["access_token"]
    with SessionLocal() as db:
        db.execute(text("update users set is_suspended = true"))
        db.commit()
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.post("/api/auth/login", json={"email": "abena@example.com", "password": "Passw0rdOK"}).status_code == 403


def test_change_password(client):
    token = register(client).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "bad", "new_password": "NewPass123"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "Passw0rdOK", "new_password": "NewPass123"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": "abena@example.com", "password": "NewPass123"}).status_code == 200


def test_categories_and_health_and_cors(client):
    assert {c["slug"] for c in client.get("/api/categories").json()} == {"plumber", "electrician"}
    assert client.get("/api/health").json()["payments_enabled"] is False
    r = client.options("/api/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.options("/api/auth/login", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
