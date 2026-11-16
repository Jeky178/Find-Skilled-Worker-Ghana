from database import SessionLocal
from models import User, UserRole
from auth import hash_password

MSG = {"name": "Kofi Test", "email": "Kofi@Example.com", "phone": "0201234567",
       "topic": "General question", "message": "How do I list my plumbing business?"}


def admin_token(client):
    with SessionLocal() as db:
        db.add(User(full_name="Boss", email="boss@example.com", password_hash=hash_password("AdminPass1"), role=UserRole.admin))
        db.commit()
    return client.post("/api/auth/login", json={"email": "boss@example.com", "password": "AdminPass1"}).json()["access_token"]


def test_send_message_and_admin_reads_it(client):
    assert client.post("/api/contact", json=MSG).status_code == 201
    assert client.get("/api/contact").status_code == 401                       # not public
    h = {"Authorization": f"Bearer {admin_token(client)}"}
    rows = client.get("/api/contact", headers=h).json()
    assert len(rows) == 1 and rows[0]["email"] == "kofi@example.com" and rows[0]["is_read"] is False
    assert client.patch(f"/api/contact/{rows[0]['id']}/read", headers=h).json()["is_read"] is True


def test_customer_cannot_read_messages(client):
    t = client.post("/api/auth/register", json={"full_name": "Abena", "email": "a@example.com", "password": "Passw0rd1"}).json()["access_token"]
    assert client.get("/api/contact", headers={"Authorization": f"Bearer {t}"}).status_code == 403


def test_validation_and_rate_limit(client):
    assert client.post("/api/contact", json={**MSG, "topic": "Hacking"}).status_code == 422
    assert client.post("/api/contact", json={**MSG, "message": "short"}).status_code == 422
    for _ in range(5):
        assert client.post("/api/contact", json=MSG).status_code == 201
    assert client.post("/api/contact", json=MSG).status_code == 429


def test_cors_accepts_any_local_vite_port(client):
    for origin in ("http://localhost:5174", "http://127.0.0.1:5173"):
        r = client.options("/api/auth/login", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert r.headers.get("access-control-allow-origin") == origin
    r = client.options("/api/auth/login", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
