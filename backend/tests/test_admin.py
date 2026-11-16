import io
import os
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from sqlalchemy import text

from auth import hash_password
from database import SessionLocal
from models import User, UserRole

PW = "Passw0rd1"


def png(size=(80, 50)):
    b = io.BytesIO()
    Image.new("RGB", size, (90, 90, 90)).save(b, "PNG")
    return b.getvalue()


def signup(client, email, role="customer", name="Abena Mensah", **extra):
    body = {"full_name": name, "email": email, "password": PW, "role": role, "phone": "0201112222", **extra}
    if role == "artisan":
        body.setdefault("category_id", 1)
        body.setdefault("location", "Madina")
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def admin_headers(client, email="boss@example.com", name="Site Boss"):
    with SessionLocal() as db:
        db.add(User(full_name=name, email=email, password_hash=hash_password("AdminPass1"), role=UserRole.admin))
        db.commit()
    t = client.post("/api/auth/login", json={"email": email, "password": "AdminPass1"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def world(client):
    adm = admin_headers(client)
    cust = signup(client, "c@example.com")
    art = signup(client, "a@example.com", role="artisan", name="Kwame Mensah")
    return adm, cust, art


def apply(client, h, id_type="Ghana Card", doc=None, cert=None):
    files = {"document": ("id.png", doc if doc is not None else png(), "image/png")}
    if cert:
        files["certificate"] = ("cert.png", cert, "image/png")
    return client.post("/api/artisan/me/verification", headers=h, data={"id_type": id_type}, files=files)


# ------------------------------------------------------------- access control
def test_admin_endpoints_are_admin_only(client):
    adm, cust, art = world(client)
    for path in ("/api/admin/stats", "/api/admin/users", "/api/admin/verifications", "/api/admin/categories",
                 "/api/admin/requests", "/api/admin/reports", "/api/admin/activity"):
        assert client.get(path).status_code == 401, path
        assert client.get(path, headers=cust).status_code == 403, path
        assert client.get(path, headers=art).status_code == 403, path
        assert client.get(path, headers=adm).status_code == 200, path
    assert client.post("/api/admin/users/2/suspend", headers=cust, json={"reason": "test"}).status_code == 403
    assert client.post("/api/admin/artisans/1/feature", headers=art, json={"featured": True}).status_code == 403


def test_stats(client):
    adm, cust, art = world(client)
    s = client.get("/api/admin/stats", headers=adm).json()
    assert (s["customers"], s["artisans"], s["admins"]) == (1, 1, 1)
    assert s["verification_unverified"] == 1 and s["requests_total"] == 0 and s["open_reports"] == 0


# ------------------------------------------------------------ users + suspend
def test_user_list_filters_and_suspension(client):
    adm, cust, art = world(client)
    users = client.get("/api/admin/users", headers=adm).json()
    assert users["total"] == 3
    assert [u["full_name"] for u in client.get("/api/admin/users?role=artisan", headers=adm).json()["items"]] == ["Kwame Mensah"]
    assert client.get("/api/admin/users?q=kwame", headers=adm).json()["total"] == 1
    assert client.get("/api/admin/users?q=%25", headers=adm).json()["total"] == 0
    art_row = client.get("/api/admin/users?role=artisan", headers=adm).json()["items"][0]
    assert art_row["artisan_id"] == 1 and art_row["category"] == "Plumber" and art_row["verification_status"] == "unverified"

    uid = art_row["id"]
    assert client.post(f"/api/admin/users/{uid}/suspend", headers=adm, json={"reason": "x"}).status_code == 422       # reason required
    r = client.post(f"/api/admin/users/{uid}/suspend", headers=adm, json={"reason": "Asked customers for deposits"})
    assert r.status_code == 200 and r.json()["is_suspended"] is True
    assert client.get("/api/auth/me", headers=art).status_code == 403                                                 # locked out at once
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": PW}).status_code == 403
    assert client.get("/api/artisans/1").status_code == 404                                                          # hidden publicly
    assert client.get("/api/admin/users?state=suspended", headers=adm).json()["total"] == 1
    assert client.post(f"/api/admin/users/{uid}/unsuspend", headers=adm).json()["is_suspended"] is False
    assert client.get("/api/artisans/1").status_code == 200


def test_admins_cannot_be_suspended(client):
    adm, *_ = world(client)
    other = admin_headers(client, "second@example.com", "Second Admin")
    ids = {u["email"]: u["id"] for u in client.get("/api/admin/users", headers=adm).json()["items"]}
    assert client.post(f"/api/admin/users/{ids['boss@example.com']}/suspend", headers=adm, json={"reason": "oops"}).status_code == 400
    assert client.post(f"/api/admin/users/{ids['second@example.com']}/suspend", headers=adm, json={"reason": "oops"}).status_code == 400
    assert client.post("/api/admin/users/999/suspend", headers=adm, json={"reason": "nope nope"}).status_code == 404


# --------------------------------------------------------------- verification
def test_verification_flow_approve(client):
    adm, cust, art = world(client)
    assert client.get("/api/artisan/me/verification", headers=art).json()["status"] == "unverified"
    assert apply(client, art, id_type="Library card").status_code == 422
    assert apply(client, art, doc=b"not an image").status_code == 400
    assert apply(client, cust).status_code == 403
    r = apply(client, art, cert=png())
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert apply(client, art).status_code == 409                                                                   # already pending
    assert client.get("/api/admin/stats", headers=adm).json()["verification_pending"] == 1
    assert "New verification application" in str(client.get("/api/notifications", headers=adm).json())            # admins notified

    queue = client.get("/api/admin/verifications?status=pending", headers=adm).json()
    v = queue["items"][0]
    assert v["artisan_name"] == "Kwame Mensah" and v["has_certificate"] is True and queue["total"] == 1

    # ID documents are private: no public URL, admin-only download
    stored = list(Path(os.environ["UPLOAD_DIR"], "private", "verification").glob("*.jpg"))
    assert len(stored) == 2
    assert not list(Path(os.environ["UPLOAD_DIR"], "public").rglob("*.jpg")) or all("verification" not in str(p) for p in Path(os.environ["UPLOAD_DIR"], "public").rglob("*.jpg"))
    assert client.get(f"/uploads/verification/{stored[0].name}").status_code == 404
    assert client.get(f"/api/admin/verifications/{v['id']}/document").status_code == 401
    assert client.get(f"/api/admin/verifications/{v['id']}/document", headers=art).status_code == 403
    assert client.get(f"/api/admin/verifications/{v['id']}/document", headers=cust).status_code == 403
    img = client.get(f"/api/admin/verifications/{v['id']}/document", headers=adm)
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg" and img.headers["cache-control"] == "no-store"
    assert client.get(f"/api/admin/verifications/{v['id']}/document?kind=certificate", headers=adm).status_code == 200
    assert client.get("/api/admin/verifications/999/document", headers=adm).status_code == 404

    d = client.post(f"/api/admin/verifications/{v['id']}/decision", headers=adm, json={"approve": True})
    assert d.status_code == 200 and d.json()["status"] == "approved"
    assert client.get("/api/artisans/1").json()["verification_status"] == "approved"
    assert client.get("/api/artisans?verified_only=true").json()["total"] == 1
    assert client.get("/api/notifications", headers=art).json()["items"][0]["title"] == "You are verified"
    assert client.post(f"/api/admin/verifications/{v['id']}/decision", headers=adm, json={"approve": False, "note": "late"}).status_code == 409
    assert apply(client, art).status_code == 409                                                                   # already verified


def test_verification_rejection_and_reapply(client):
    adm, cust, art = world(client)
    apply(client, art)
    vid = client.get("/api/admin/verifications", headers=adm).json()["items"][0]["id"]
    assert client.post(f"/api/admin/verifications/{vid}/decision", headers=adm, json={"approve": False}).status_code == 422   # reason needed
    r = client.post(f"/api/admin/verifications/{vid}/decision", headers=adm, json={"approve": False, "note": "ID photo is blurry"})
    assert r.json()["status"] == "rejected"
    mine = client.get("/api/artisan/me/verification", headers=art).json()
    assert mine["status"] == "rejected" and mine["admin_note"] == "ID photo is blurry"
    assert "blurry" in client.get("/api/notifications", headers=art).json()["items"][0]["message"]
    assert client.get("/api/artisans/1").json()["verification_status"] == "rejected"
    assert apply(client, art).status_code == 201                                                                    # may apply again
    assert client.get("/api/admin/verifications?status=pending", headers=adm).json()["total"] == 1


# ------------------------------------------------------------------ categories
def test_category_management(client):
    adm, cust, art = world(client)
    r = client.post("/api/admin/categories", headers=adm, json={"name": "  Roof   Repair ", "description": "Leaks and sheets", "icon": "home"})
    assert r.status_code == 201 and r.json()["slug"] == "roof-repair" and r.json()["name"] == "Roof Repair"
    assert client.post("/api/admin/categories", headers=adm, json={"name": "roof repair"}).status_code == 409
    assert client.post("/api/admin/categories", headers=adm, json={"name": "x"}).status_code == 422
    cid = r.json()["id"]
    assert client.patch(f"/api/admin/categories/{cid}", headers=adm, json={"name": "Roofing", "description": "Roof work"}).json()["slug"] == "roof-repair"
    assert client.patch(f"/api/admin/categories/{cid}", headers=adm, json={"name": "Plumber"}).status_code == 409
    assert "Roofing" in [c["name"] for c in client.get("/api/categories").json()]

    # deactivating hides it everywhere public; the plumber (with an artisan) disappears from the directory
    assert client.patch("/api/admin/categories/1", headers=adm, json={"is_active": False}).json()["artisan_count"] == 1
    assert "plumber" not in [c["slug"] for c in client.get("/api/categories").json()]
    assert client.get("/api/artisans").json()["total"] == 0
    assert client.post("/api/auth/register", json={"full_name": "New Guy", "email": "n@example.com", "password": PW, "role": "artisan", "category_id": 1}).status_code == 422
    assert client.patch("/api/admin/categories/1", headers=adm, json={"is_active": True}).status_code == 200
    assert client.get("/api/artisans").json()["total"] == 1
    assert client.patch("/api/admin/categories/99", headers=adm, json={"is_active": False}).status_code == 404


# --------------------------------------------------------------------- reports
def test_report_flow(client):
    adm, cust, art = world(client)
    rep = lambda h, **b: client.post("/api/reports", headers=h, json=b)  # noqa: E731
    assert client.get("/api/reports/reasons").json()[0] == "Fake or misleading profile"
    assert rep(cust, artisan_id=1, reason="Made up reason").status_code == 422
    assert rep(cust, reason="Scam or fraud").status_code == 422                                  # needs a target
    assert rep(cust, artisan_id=1, request_id=1, reason="Scam or fraud").status_code == 422      # not both
    assert rep(cust, artisan_id=99, reason="Scam or fraud").status_code == 404
    assert rep(art, artisan_id=1, reason="Scam or fraud").status_code == 400                     # cannot report yourself
    assert rep(adm, artisan_id=1, reason="Scam or fraud").status_code == 403
    r = rep(cust, artisan_id=1, reason="Scam or fraud", details="Asked me to send money first")
    assert r.status_code == 201
    assert rep(cust, artisan_id=1, reason="Scam or fraud").status_code == 409                    # duplicate open report
    assert "New report" in str(client.get("/api/notifications", headers=adm).json())

    rows = client.get("/api/admin/reports", headers=adm).json()
    assert rows["total"] == 1 and rows["items"][0]["reported_name"] == "Kwame Mensah" and rows["items"][0]["reporter_name"] == "Abena Mensah"
    rid = rows["items"][0]["id"]
    assert client.get("/api/admin/stats", headers=adm).json()["open_reports"] == 1
    assert client.patch(f"/api/admin/reports/{rid}", headers=adm, json={"status": "resolved"}).status_code == 422      # outcome note needed
    assert client.patch(f"/api/admin/reports/{rid}", headers=adm, json={"status": "reviewing"}).json()["status"] == "reviewing"
    done = client.patch(f"/api/admin/reports/{rid}", headers=adm, json={"status": "resolved", "admin_note": "Account suspended"})
    assert done.json()["status"] == "resolved"
    assert "Account suspended" in client.get("/api/notifications", headers=cust).json()["items"][0]["message"]       # reporter told
    assert client.get("/api/admin/stats", headers=adm).json()["open_reports"] == 0
    assert client.get("/api/admin/reports?status=resolved", headers=adm).json()["total"] == 1


def test_report_from_a_request_and_daily_limit(client):
    adm, cust, art = world(client)
    stranger = signup(client, "s@example.com", name="Stranger Danger")
    form = {"artisan_id": 1, "title": "Leaking sink", "description": "Water everywhere under the sink.", "location": "Madina"}
    rid = client.post("/api/requests", headers=cust, data=form).json()["id"]
    assert client.post("/api/reports", headers=stranger, json={"request_id": rid, "reason": "Other"}).status_code == 404   # not a participant
    r = client.post("/api/reports", headers=art, json={"request_id": rid, "reason": "Harassment or abuse"})              # artisan reports the customer
    assert r.status_code == 201
    row = client.get("/api/admin/reports", headers=adm).json()["items"][0]
    assert row["reported_name"] == "Abena Mensah" and row["request_title"] == "Leaking sink"
    reasons = ["Fake or misleading profile", "Unprofessional behaviour", "Poor or unfinished work",
               "Asked for payment outside the platform", "Scam or fraud", "Harassment or abuse"]
    for i, reason in enumerate(reasons):                                                                                 # the customer's own count starts at 0
        status = client.post("/api/reports", headers=cust, json={"artisan_id": 1, "reason": reason}).status_code
        assert status == (201 if i < 5 else 429)                                                                         # 5 per day


# ------------------------------------------------------------ featured + plans
def test_featured_listings_and_expiry(client):
    adm, cust, art = world(client)
    signup(client, "y@example.com", role="artisan", name="Yaw Boateng", category_id=2)
    assert client.post("/api/admin/artisans/99/feature", headers=adm, json={"featured": True}).status_code == 404
    soon = str(date.today() + timedelta(days=30))
    r = client.post("/api/admin/artisans/2/feature", headers=adm, json={"featured": True, "until": soon})
    assert r.status_code == 200 and r.json()["is_featured"] is True
    assert client.post("/api/admin/artisans/2/feature", headers=adm, json={"featured": True, "until": str(date.today() - timedelta(days=1))}).status_code == 422
    assert [i["name"] for i in client.get("/api/artisans?featured_only=true").json()["items"]] == ["Yaw Boateng"]
    assert client.get("/api/artisans").json()["items"][0]["name"] == "Yaw Boateng"                                       # priority visibility
    # an expired featured listing silently stops being featured
    with SessionLocal() as db:
        db.execute(text("update artisan_profiles set featured_until = '2020-01-01 00:00:00' where id = 2")); db.commit()
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 0
    assert client.get("/api/artisans/2").json()["is_featured"] is False
    client.post("/api/admin/artisans/2/feature", headers=adm, json={"featured": True})                                  # no end date
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 1
    client.post("/api/admin/artisans/2/feature", headers=adm, json={"featured": False})
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 0


def test_complimentary_plan_change_records_no_payment(client):
    adm, cust, art = world(client)
    assert client.post("/api/admin/artisans/1/plan", headers=adm, json={"plan": "premium"}).json()["plan"] == "premium"
    assert client.get("/api/artisan/me", headers=art).json()["portfolio_limit"] == 30
    assert client.post("/api/admin/artisans/1/plan", headers=adm, json={"plan": "gold"}).status_code == 422
    with SessionLocal() as db:
        assert db.execute(text("select count(*) from payments")).scalar() == 0
        assert "no payment" in db.execute(text("select detail from admin_actions where action='set_plan'")).scalar()


# -------------------------------------------------- monitoring + audit trail
def test_request_monitor_and_activity_feed(client):
    adm, cust, art = world(client)
    form = {"artisan_id": 1, "title": "Burst pipe", "description": "A pipe burst in the wall.", "location": "Madina"}
    rid = client.post("/api/requests", headers=cust, data=form).json()["id"]
    reqs = client.get("/api/admin/requests", headers=adm).json()
    assert reqs["total"] == 1 and reqs["items"][0]["customer_name"] == "Abena Mensah" and reqs["items"][0]["artisan_name"] == "Kwame Mensah"
    assert client.get("/api/admin/requests?status=completed", headers=adm).json()["total"] == 0
    assert client.get("/api/admin/requests?q=pipe", headers=adm).json()["total"] == 1
    assert client.get(f"/api/requests/{rid}", headers=adm).json()["viewer_role"] == "admin"                            # admin may view
    assert client.patch(f"/api/requests/{rid}/status", headers=adm, json={"status": "cancelled"}).status_code == 403    # but not change

    client.post("/api/admin/users/2/suspend", headers=adm, json={"reason": "Testing the audit log"})
    feed = client.get("/api/admin/activity", headers=adm).json()
    text_all = " | ".join(i["text"] for i in feed)
    assert "requested Kwame Mensah: Burst pipe" in text_all and "New artisan registered" in text_all
    assert "suspend user" in text_all and "Site Boss" in text_all                                                       # audit entry names the admin
    assert [i["at"] for i in feed] == sorted([i["at"] for i in feed], reverse=True)
