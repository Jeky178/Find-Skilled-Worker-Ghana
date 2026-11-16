import io
from datetime import date, timedelta

from PIL import Image
from sqlalchemy import text

from database import SessionLocal

PW = "Passw0rd1"


def png(size=(50, 40)):
    b = io.BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(b, "PNG")
    return b.getvalue()


def signup(client, email, role="customer", name="Abena Mensah", **extra):
    body = {"full_name": name, "email": email, "password": PW, "role": role, "phone": "0201112222", **extra}
    if role == "artisan":
        body.setdefault("category_id", 1)
        body.setdefault("location", "Madina")
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def world(client):
    """customer Abena, artisan Kwame (profile id 1), another customer Kofi, another artisan Yaw (profile id 2)."""
    c = signup(client, "c@example.com")
    a = signup(client, "a@example.com", role="artisan", name="Kwame Mensah")
    client.patch("/api/artisan/me", headers=a, json={"whatsapp_number": "0241234567"})
    c2 = signup(client, "c2@example.com", name="Kofi Ansah")
    a2 = signup(client, "a2@example.com", role="artisan", name="Yaw Boateng")
    return c, a, c2, a2


def make_request(client, h, artisan_id=1, title="Leaking kitchen sink", photos=0, **extra):
    data = {"artisan_id": artisan_id, "title": title, "description": "Water drips under the sink all day.",
            "location": "Madina", **extra}
    files = [("photos", (f"p{i}.png", png(), "image/png")) for i in range(photos)]
    return client.post("/api/requests", headers=h, data=data, files=files or None)


def move(client, h, rid, status, note=None):
    return client.patch(f"/api/requests/{rid}/status", headers=h, json={"status": status, "note": note})


# ------------------------------------------------------------------ creating
def test_customer_creates_request_with_photos_and_artisan_is_notified(client):
    c, a, *_ = world(client)
    r = make_request(client, c, photos=2, preferred_date=str(date.today() + timedelta(days=3)))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "pending" and len(d["photos"]) == 2 and d["viewer_role"] == "customer"
    assert d["allowed_actions"] == ["cancelled"] and d["artisan"]["name"] == "Kwame Mensah"
    assert d["other_contact"]["whatsapp_url"].startswith("https://wa.me/233241234567")      # customer can WhatsApp artisan
    n = client.get("/api/notifications", headers=a).json()
    assert n["unread"] == 1 and n["items"][0]["title"] == "New service request" and n["items"][0]["link"] == f"/requests/{d['id']}"


def test_create_validation_and_rules(client):
    c, a, *_ = world(client)
    assert make_request(client, a).status_code == 403                                      # artisans cannot request
    assert client.post("/api/requests", data={"artisan_id": 1}).status_code == 401
    assert make_request(client, c, title="ab").status_code == 422
    assert make_request(client, c, artisan_id=999).status_code == 404
    assert make_request(client, c, photos=6).status_code == 422
    assert make_request(client, c, preferred_date=str(date.today() - timedelta(days=1))).status_code == 422
    bad = client.post("/api/requests", headers=c, data={"artisan_id": 1, "title": "Broken pipe", "description": "Pipe burst in the wall.",
                      "location": "Madina"}, files=[("photos", ("x.png", b"not an image", "image/png"))])
    assert bad.status_code == 400
    assert client.get("/api/requests/mine", headers=c).json()["total"] == 0                # nothing half-saved
    assert make_request(client, c).status_code == 201
    assert make_request(client, c, title="LEAKING KITCHEN SINK").status_code == 409        # duplicate open request
    client.patch("/api/artisan/me", headers=a, json={"is_available": False})
    assert make_request(client, c, title="Another job").status_code == 409                 # unavailable artisan


def test_daily_request_limit(client):
    c, *_ = world(client)
    for i in range(10):
        assert make_request(client, c, artisan_id=2, title=f"Job number {i}").status_code == 201
    assert make_request(client, c, artisan_id=2, title="One too many").status_code == 429


# ------------------------------------------------------------- access control
def test_only_participants_can_view(client):
    c, a, c2, a2 = world(client)
    rid = make_request(client, c).json()["id"]
    assert client.get(f"/api/requests/{rid}", headers=c).status_code == 200
    assert client.get(f"/api/requests/{rid}", headers=a).status_code == 200
    assert client.get(f"/api/requests/{rid}", headers=c2).status_code == 404               # other customer
    assert client.get(f"/api/requests/{rid}", headers=a2).status_code == 404               # other artisan
    assert client.get(f"/api/requests/{rid}").status_code == 401
    assert client.get("/api/requests/mine", headers=a2).json()["total"] == 0
    assert client.get("/api/requests/mine", headers=a).json()["items"][0]["other_party"]["name"] == "Abena Mensah"
    assert client.get("/api/requests/mine", headers=c).json()["items"][0]["other_party"]["name"] == "Kwame Mensah"
    assert move(client, c2, rid, "cancelled").status_code == 404
    assert move(client, a2, rid, "accepted").status_code == 404


# -------------------------------------------------------------------- status
def test_full_job_lifecycle_with_contact_privacy(client):
    c, a, *_ = world(client)
    rid = make_request(client, c).json()["id"]
    assert client.get(f"/api/requests/{rid}", headers=a).json()["other_contact"] is None   # hidden until accepted
    assert client.get(f"/api/requests/{rid}", headers=a).json()["allowed_actions"] == ["accepted", "rejected"]

    d = move(client, a, rid, "accepted").json()
    assert d["status"] == "accepted" and d["other_contact"]["phone"] == "233201112222"      # now shared
    assert d["other_contact"]["whatsapp_url"].startswith("https://wa.me/233201112222")
    assert client.get("/api/notifications", headers=c).json()["items"][0]["title"] == "Request accepted"

    assert move(client, a, rid, "in_progress").json()["status"] == "in_progress"
    assert move(client, a, rid, "completed").json()["status"] == "completed"
    assert "Please rate" in client.get("/api/notifications", headers=c).json()["items"][0]["message"]
    assert move(client, a, rid, "cancelled").status_code == 409                            # finished jobs are final
    assert client.get("/api/requests/summary", headers=c).json() == {"pending": 0, "active": 0, "completed": 1, "total": 1}


def test_invalid_transitions_and_required_notes(client):
    c, a, *_ = world(client)
    rid = make_request(client, c).json()["id"]
    assert move(client, c, rid, "accepted").status_code == 409                             # customers cannot accept
    assert move(client, a, rid, "completed").status_code == 409                            # cannot skip steps
    assert move(client, a, rid, "rejected").status_code == 422                             # reason required
    r = move(client, a, rid, "rejected", "Fully booked this week")
    assert r.json()["status"] == "rejected" and r.json()["status_note"] == "Fully booked this week"
    assert "Fully booked" in client.get("/api/notifications", headers=c).json()["items"][0]["message"]
    assert move(client, c, rid, "cancelled").status_code == 409                            # already closed
    # customer cancel + artisan cancel
    r2 = make_request(client, c, title="Second job").json()["id"]
    assert move(client, c, r2, "cancelled").json()["status"] == "cancelled"
    r3 = make_request(client, c, title="Third job").json()["id"]
    move(client, a, r3, "accepted")
    assert move(client, a, r3, "cancelled").status_code == 422                             # artisan must explain
    assert move(client, a, r3, "cancelled", "Tools broke").json()["status"] == "cancelled"


def test_customer_can_confirm_completion(client):
    c, a, *_ = world(client)
    rid = make_request(client, c).json()["id"]
    move(client, a, rid, "accepted"); move(client, a, rid, "in_progress")
    assert move(client, c, rid, "completed").json()["status"] == "completed"
    assert "marked this job as completed" in client.get("/api/notifications", headers=a).json()["items"][0]["message"]


def test_list_filters(client):
    c, a, *_ = world(client)
    r1 = make_request(client, c, title="First job").json()["id"]
    make_request(client, c, title="Second job")
    move(client, a, r1, "rejected", "No time")
    assert client.get("/api/requests/mine?status=active", headers=c).json()["total"] == 1
    assert client.get("/api/requests/mine?status=closed", headers=c).json()["total"] == 1
    assert client.get("/api/requests/mine?status=rejected", headers=c).json()["total"] == 1
    assert client.get("/api/requests/mine?status=nonsense", headers=c).status_code == 422


# -------------------------------------------------------------------- reviews
def completed_job(client, c, a, title="Leaking kitchen sink"):
    rid = make_request(client, c, title=title).json()["id"]
    move(client, a, rid, "accepted"); move(client, a, rid, "in_progress"); move(client, a, rid, "completed")
    return rid


def test_review_rules_and_rating_average(client):
    c, a, c2, _ = world(client)
    rid = make_request(client, c).json()["id"]
    review = lambda h, rid, rating=5, comment="Great work": client.post(f"/api/requests/{rid}/review", headers=h, json={"rating": rating, "comment": comment})  # noqa: E731
    assert review(c, rid).status_code == 409                                               # not completed yet
    move(client, a, rid, "accepted"); move(client, a, rid, "in_progress"); move(client, a, rid, "completed")
    assert review(c, rid, rating=6).status_code == 422 and review(c, rid, rating=0).status_code == 422
    assert review(a, rid).status_code == 403                                               # artisan cannot review themselves
    assert review(c2, rid).status_code == 404                                              # stranger
    r = review(c, rid, 4, "  Fixed quickly  ")
    assert r.status_code == 201 and r.json()["comment"] == "Fixed quickly" and r.json()["reviewer_name"] == "Abena M."
    assert review(c, rid).status_code == 409                                               # only once
    p = client.get("/api/artisans/1").json()
    assert (p["review_count"], float(p["avg_rating"])) == (1, 4.0)

    rid2 = completed_job(client, c2, a, "Bathroom tap")
    review(c2, rid2, 5)
    p = client.get("/api/artisans/1").json()
    assert (p["review_count"], float(p["avg_rating"])) == (2, 4.5)                         # average recomputed
    assert client.get(f"/api/requests/{rid}", headers=a).json()["review"]["rating"] == 4
    assert client.get("/api/notifications", headers=a).json()["items"][0]["title"] == "New 5-star review"


def test_review_lists_are_public_and_private_parts_hidden(client):
    c, a, *_ = world(client)
    rid = completed_job(client, c, a)
    client.post(f"/api/requests/{rid}/review", headers=c, json={"rating": 5, "comment": "Excellent"})
    pub = client.get("/api/artisans/1/reviews").json()
    assert pub["total"] == 1 and pub["items"][0]["reviewer_name"] == "Abena M." and pub["items"][0]["artisan_name"] is None
    assert "c@example.com" not in str(pub) and "Leaking" not in str(pub)                   # no email or job title in public view
    assert client.get("/api/artisans/999/reviews").status_code == 404
    mine_a = client.get("/api/reviews/mine", headers=a).json()                             # received
    assert mine_a["total"] == 1 and float(mine_a["avg_rating"]) == 5.0
    mine_c = client.get("/api/reviews/mine", headers=c).json()                             # written
    assert mine_c["items"][0]["artisan_name"] == "Kwame Mensah" and mine_c["items"][0]["category"] == "Plumber"


# -------------------------------------------------------------- notifications
def test_notifications_read_state_and_isolation(client):
    c, a, c2, _ = world(client)
    rid = make_request(client, c).json()["id"]
    make_request(client, c, title="Another job")
    assert client.get("/api/notifications/unread-count", headers=a).json() == {"unread": 2}
    assert client.get("/api/notifications/unread-count", headers=c).json() == {"unread": 0}
    first = client.get("/api/notifications", headers=a).json()["items"][0]["id"]
    assert client.post(f"/api/notifications/{first}/read", headers=c).status_code == 404   # not yours
    assert client.post(f"/api/notifications/{first}/read", headers=a).json()["is_read"] is True
    assert client.get("/api/notifications/unread-count", headers=a).json() == {"unread": 1}
    assert client.get("/api/notifications?unread_only=true", headers=a).json()["total"] == 1
    assert client.post("/api/notifications/read-all", headers=a).status_code == 204
    assert client.get("/api/notifications/unread-count", headers=a).json() == {"unread": 0}
    assert client.get("/api/notifications").status_code == 401
