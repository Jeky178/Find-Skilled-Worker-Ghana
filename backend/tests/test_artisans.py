import io
import os
from pathlib import Path

from PIL import Image
from sqlalchemy import text

from database import SessionLocal

PW = "Passw0rd1"


def png_bytes(size=(60, 40), fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 80, 20)).save(buf, fmt)
    return buf.getvalue()


def signup(client, email, role="artisan", name="Kwame Mensah", **extra):
    body = {"full_name": name, "email": email, "password": PW, "role": role, **extra}
    if role == "artisan":
        body.setdefault("category_id", 1)
        body.setdefault("location", "Madina")
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(client, url, h, data, name="x.png", ctype="image/png", **form):
    return client.post(url, headers=h, files={"file": (name, data, ctype)}, data=form)


# ------------------------------------------------------------- profile editing
def test_artisan_can_edit_profile(client):
    h = signup(client, "k@example.com")
    r = client.patch("/api/artisan/me", headers=h, json={
        "headline": "Reliable plumber", "bio": "I fix leaks and install pipes. " * 3, "years_experience": 8,
        "whatsapp_number": "0241234567", "price_min": 80, "price_max": 300, "price_note": "Per visit",
        "locations": ["madina", "ADENTA", "Madina"], "category_id": 2,
    })
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["locations"] == ["Adenta", "Madina"]                    # cleaned, de-duplicated
    assert me["whatsapp_number"] == "233241234567" and me["category"]["slug"] == "electrician"
    assert me["completeness"] == 70 and "Add a profile photo" in me["missing"]
    # removing an area works too
    assert client.patch("/api/artisan/me", headers=h, json={"locations": ["Adenta"]}).json()["locations"] == ["Adenta"]


def test_profile_validation(client):
    h = signup(client, "k@example.com")
    assert client.patch("/api/artisan/me", headers=h, json={"price_min": 500, "price_max": 100}).status_code == 422
    assert client.patch("/api/artisan/me", headers=h, json={"price_min": 500}).status_code == 200
    assert client.patch("/api/artisan/me", headers=h, json={"price_max": 100}).status_code == 422   # vs stored min
    assert client.patch("/api/artisan/me", headers=h, json={"years_experience": 99}).status_code == 422
    assert client.patch("/api/artisan/me", headers=h, json={"whatsapp_number": "123"}).status_code == 422
    assert client.patch("/api/artisan/me", headers=h, json={"category_id": 99}).status_code == 422
    assert client.patch("/api/artisan/me", headers=h, json={"locations": ["x"]}).status_code == 422


def test_only_artisans_can_use_artisan_endpoints(client):
    cust = signup(client, "c@example.com", role="customer", name="Abena")
    assert client.get("/api/artisan/me", headers=cust).status_code == 403
    assert client.get("/api/artisan/me").status_code == 401
    assert client.patch("/api/artisan/me", headers=cust, json={"headline": "x"}).status_code == 403


# ------------------------------------------------------------------- uploads
def test_profile_photo_upload_is_validated_and_reencoded(client):
    h = signup(client, "k@example.com")
    r = upload(client, "/api/artisan/me/photo", h, png_bytes((3000, 2000)))
    assert r.status_code == 200, r.text
    url = r.json()["profile_image"]
    assert url.startswith("/uploads/profiles/") and url.endswith(".jpg")
    stored = Path(os.environ["UPLOAD_DIR"], "public", url.removeprefix("/uploads/"))
    img = Image.open(stored)
    assert img.format == "JPEG" and max(img.size) <= 1600                   # re-encoded + resized
    assert client.get(url).status_code == 200                               # served publicly
    # replacing the photo deletes the old file
    r2 = upload(client, "/api/artisan/me/photo", h, png_bytes())
    assert not stored.exists() and r2.json()["profile_image"] != url


def test_bad_uploads_are_rejected(client):
    h = signup(client, "k@example.com")
    url = "/api/artisan/me/photo"
    assert upload(client, url, h, b"MZ\x90\x00 this is an exe", "evil.png", "image/png").status_code == 400       # not an image
    assert upload(client, url, h, b"<svg onload=alert(1)></svg>", "a.svg", "image/svg+xml").status_code == 400
    assert upload(client, url, h, b"", "empty.png").status_code == 400
    assert upload(client, url, h, png_bytes(fmt="GIF"), "a.gif", "image/gif").status_code == 400                # GIF not allowed
    assert upload(client, url, h, b"\x89PNG\r\n\x1a\n" + b"junk" * 50, "t.png").status_code == 400            # truncated PNG
    big = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 10)
    assert upload(client, url, h, big, "big.jpg", "image/jpeg").status_code == 413
    # a real image with a lying filename and content-type is still accepted (content is what counts)
    assert upload(client, url, h, png_bytes(), "photo.exe", "application/octet-stream").status_code == 200
    # customers cannot upload
    cust = signup(client, "c@example.com", role="customer", name="Abena")
    assert upload(client, url, cust, png_bytes()).status_code == 403


def test_portfolio_add_delete_and_free_plan_limit(client):
    h = signup(client, "k@example.com")
    ids = []
    for i in range(5):
        r = upload(client, "/api/artisan/me/portfolio", h, png_bytes(), caption=f"Job {i}")
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    r = upload(client, "/api/artisan/me/portfolio", h, png_bytes())
    assert r.status_code == 403 and "5 portfolio photos" in r.json()["detail"]        # free plan limit
    assert client.delete(f"/api/artisan/me/portfolio/{ids[0]}", headers=h).status_code == 204
    assert upload(client, "/api/artisan/me/portfolio", h, png_bytes()).status_code == 201
    # premium gets more
    with SessionLocal() as db:
        db.execute(text("update artisan_profiles set plan = 'premium'")); db.commit()
    assert upload(client, "/api/artisan/me/portfolio", h, png_bytes()).status_code == 201
    assert client.get("/api/artisan/me", headers=h).json()["portfolio_limit"] == 30


def test_cannot_delete_someone_elses_photo(client):
    a = signup(client, "a@example.com")
    b = signup(client, "b@example.com", name="Yaw Boateng")
    item = upload(client, "/api/artisan/me/portfolio", a, png_bytes()).json()["id"]
    assert client.delete(f"/api/artisan/me/portfolio/{item}", headers=b).status_code == 404
    assert client.delete(f"/api/artisan/me/portfolio/{item}", headers=a).status_code == 204


# ----------------------------------------------------------------- directory
def make_directory(client):
    """Kwame (plumber, Madina+Adenta), Yaw (electrician, Dome), Ama (plumber, Kasoa)."""
    k = signup(client, "k@example.com", name="Kwame Mensah", location="Madina")
    client.patch("/api/artisan/me", headers=k, json={"locations": ["Madina", "Adenta"], "headline": "Leak specialist",
                                                      "years_experience": 8, "price_min": 80, "price_max": 300,
                                                      "whatsapp_number": "0241234567"})
    y = signup(client, "y@example.com", name="Yaw Boateng", category_id=2, location="Dome")
    client.patch("/api/artisan/me", headers=y, json={"years_experience": 12, "bio": "Wiring and fittings for homes " * 3})
    a = signup(client, "a@example.com", name="Ama Serwaa", location="Kasoa")
    client.patch("/api/artisan/me", headers=a, json={"is_available": False, "price_min": 50})
    return k, y, a


def names(r):
    return [i["name"] for i in r.json()["items"]]


def test_directory_filters_and_search(client):
    make_directory(client)
    assert client.get("/api/artisans").json()["total"] == 3
    assert sorted(names(client.get("/api/artisans?category=plumber"))) == ["Ama Serwaa", "Kwame Mensah"]
    assert names(client.get("/api/artisans?location=adenta")) == ["Kwame Mensah"]                    # case-insensitive
    assert names(client.get("/api/artisans?category=plumber&location=Kasoa")) == ["Ama Serwaa"]
    assert names(client.get("/api/artisans?q=wiring")) == ["Yaw Boateng"]                            # bio
    assert names(client.get("/api/artisans?q=electric")) == ["Yaw Boateng"]                          # trade name
    assert names(client.get("/api/artisans?q=leak")) == ["Kwame Mensah"]                             # headline
    assert client.get("/api/artisans?q=%25").json()["total"] == 0                                    # % is not a wildcard
    assert sorted(names(client.get("/api/artisans?available_only=true"))) == ["Kwame Mensah", "Yaw Boateng"]
    assert client.get("/api/artisans?verified_only=true").json()["total"] == 0                       # nobody verified
    assert client.get("/api/artisans?category=nope").json()["total"] == 0


def test_directory_sorting_and_priority_visibility(client):
    make_directory(client)
    assert names(client.get("/api/artisans?sort=experience"))[0] == "Yaw Boateng"
    assert names(client.get("/api/artisans?sort=price_low"))[:2] == ["Ama Serwaa", "Kwame Mensah"]   # unpriced last
    assert names(client.get("/api/artisans?sort=newest"))[0] == "Ama Serwaa"
    with SessionLocal() as db:                                                                       # premium + featured go first
        db.execute(text("update artisan_profiles set plan='premium', is_featured=true where id=3")); db.commit()
    assert names(client.get("/api/artisans"))[0] == "Ama Serwaa"
    assert names(client.get("/api/artisans?featured_only=true")) == ["Ama Serwaa"]


def test_pagination(client):
    make_directory(client)
    r = client.get("/api/artisans?page_size=2").json()
    assert (r["total"], r["pages"], len(r["items"])) == (3, 2, 2)
    assert len(client.get("/api/artisans?page_size=2&page=2").json()["items"]) == 1
    assert client.get("/api/artisans?page_size=500").status_code == 422


def test_suspended_artisans_are_hidden(client):
    make_directory(client)
    with SessionLocal() as db:
        db.execute(text("update users set is_suspended=true where email='y@example.com'")); db.commit()
    assert "Yaw Boateng" not in names(client.get("/api/artisans"))
    assert client.get("/api/artisans/2").status_code == 404


def test_artisan_detail_and_whatsapp_link(client):
    k, _, a = make_directory(client)
    upload(client, "/api/artisan/me/portfolio", k, png_bytes(), caption="Bathroom fit-out")
    d = client.get("/api/artisans/1").json()
    assert d["name"] == "Kwame Mensah" and d["category"]["name"] == "Plumber"
    assert d["whatsapp_url"].startswith("https://wa.me/233241234567?text=Hello%20Kwame")
    assert d["portfolio"][0]["caption"] == "Bathroom fit-out"
    assert "password" not in str(d) and "email" not in d                                            # no private data
    assert client.get("/api/artisans/3").json()["whatsapp_url"] is None                             # none set
    assert client.get("/api/artisans/999").status_code == 404


def test_locations_list(client):
    make_directory(client)
    locs = {l["location"]: l["count"] for l in client.get("/api/artisans/locations").json()}
    assert locs == {"Adenta": 1, "Dome": 1, "Kasoa": 1, "Madina": 1}
