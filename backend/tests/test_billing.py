import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import text

import routers.billing as billing_router
from auth import hash_password
from config import Settings, get_settings
from database import SessionLocal
from models import ArtisanProfile, Payment, PaymentItem, Subscription, User, UserRole
from services.payments.base import PaymentProviderError
from services.payments.fulfillment import expire_due_subscriptions
from services.payments.paystack import PaystackProvider
from tests.fake_provider import FakeProvider, sign

PW = "Passw0rd1"


def signup(client, email, role="artisan", name="Kwame Mensah", **extra):
    body = {"full_name": name, "email": email, "password": PW, "role": role, "phone": "0201112222", **extra}
    if role == "artisan":
        body.setdefault("category_id", 1)
        body.setdefault("location", "Madina")
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def admin_headers(client):
    with SessionLocal() as db:
        db.add(User(full_name="Site Boss", email="boss@example.com", password_hash=hash_password("AdminPass1"), role=UserRole.admin))
        db.commit()
    return {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": "boss@example.com", "password": "AdminPass1"}).json()["access_token"]}


@pytest.fixture()
def pay(client, monkeypatch):
    """Payments switched ON with a simulated provider."""
    monkeypatch.setattr(get_settings(), "PAYSTACK_SECRET_KEY", "sk_test_secret")
    fake = FakeProvider()
    monkeypatch.setattr(billing_router, "get_provider", lambda: fake)
    return fake


def buy(client, h, code="premium_monthly", **kw):
    return client.post("/api/billing/checkout", headers=h, json={"product_code": code, **kw})


def verify(client, h, ref):
    return client.get(f"/api/billing/verify/{ref}", headers=h)


def plan_of(client, h):
    return client.get("/api/billing/me", headers=h).json()


# --------------------------------------------------------------- when payments are OFF
def test_plans_are_public_and_nothing_is_buyable_without_a_provider(client):
    plans = client.get("/api/billing/plans").json()
    assert plans["payments_enabled"] is False and plans["currency"] == "GHS"
    by_code = {p["code"]: p for p in plans["products"]}
    assert Decimal(by_code["premium_monthly"]["price_ghs"]) == 50 and by_code["premium_monthly"]["purchasable"] is False
    assert by_code["business_plan"]["coming_soon"] is True
    art = signup(client, "a@example.com")
    r = buy(client, art)
    assert r.status_code == 503 and "not switched on" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.query(Payment).count() == 0                         # nothing recorded, nothing pretended
    assert client.post("/api/billing/webhook/paystack", content=b"{}").status_code == 503


def test_billing_is_artisan_only(client, pay):
    cust = signup(client, "c@example.com", role="customer", name="Abena")
    assert buy(client, cust).status_code == 403
    assert client.get("/api/billing/me", headers=cust).status_code == 403
    assert client.get("/api/billing/history", headers=cust).status_code == 403
    assert client.post("/api/billing/checkout", json={"product_code": "premium_monthly"}).status_code == 401


# --------------------------------------------------------------- checkout and verification
def test_checkout_creates_pending_payment_and_grants_nothing_yet(client, pay):
    art = signup(client, "a@example.com")
    r = buy(client, art, channel="mobile_money")
    assert r.status_code == 201, r.text
    ref = r.json()["reference"]
    assert ref.startswith("FSW-") and r.json()["authorization_url"] == f"https://checkout.test/pay/{ref}"
    sent = pay.initialized[0]
    assert sent["amount"] == Decimal("50") and sent["currency"] == "GHS" and sent["channel"] == "mobile_money"
    assert sent["email"] == "a@example.com" and sent["callback_url"].endswith("/billing/callback")
    assert plan_of(client, art)["plan"] == "free" and plan_of(client, art)["premium_until"] is None
    hist = client.get("/api/billing/history", headers=art).json()
    assert hist[0]["status"] == "pending" and hist[0]["fulfilled"] is False and hist[0]["product_name"] == "Premium, 1 month"
    assert buy(client, art, "nonsense").status_code == 404
    assert buy(client, art, "business_plan").status_code == 404           # coming soon
    assert buy(client, art, "verification").status_code == 404            # fee is 0 = not for sale


def test_provider_outage_marks_payment_failed(client, pay):
    art = signup(client, "a@example.com")
    pay.unreachable = True
    r = buy(client, art)
    assert r.status_code == 502 and "Could not reach" in r.json()["detail"]
    assert client.get("/api/billing/history", headers=art).json()[0]["status"] == "failed"


def test_verified_payment_activates_premium_exactly_once(client, pay):
    art = signup(client, "a@example.com")
    ref = buy(client, art).json()["reference"]
    assert verify(client, art, ref).json()["status"] == "pending"          # provider has not confirmed yet
    assert plan_of(client, art)["plan"] == "free"

    pay.succeed(ref, "50")
    v = verify(client, art, ref).json()
    assert v["status"] == "completed" and v["product_code"] == "premium_monthly"
    me = plan_of(client, art)
    assert me["plan"] == "premium" and me["premium_until"] is not None
    until = datetime.fromisoformat(me["premium_until"].replace("Z", "+00:00"))
    until = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
    assert 29 <= (until - datetime.now(timezone.utc)).days <= 30
    assert client.get("/api/artisans/1").json()["plan"] == "premium" and client.get("/api/artisan/me", headers=art).json()["portfolio_limit"] == 30
    assert "Premium is active" in client.get("/api/notifications", headers=art).json()["items"][0]["title"]

    for _ in range(3):                                                    # callback pressed again and again
        assert verify(client, art, ref).json()["status"] == "completed"
    with SessionLocal() as db:
        assert db.query(Subscription).count() == 1                        # still only one subscription
        assert db.query(Payment).one().paid_at is not None
    assert client.get("/api/billing/history", headers=art).json()[0]["fulfilled"] is True


def test_cannot_verify_someone_elses_payment(client, pay):
    a = signup(client, "a@example.com")
    b = signup(client, "b@example.com", name="Yaw Boateng")
    ref = buy(client, a).json()["reference"]
    pay.succeed(ref, "50")
    assert verify(client, b, ref).status_code == 404
    assert plan_of(client, b)["plan"] == "free"


def test_underpayment_or_wrong_currency_is_never_fulfilled(client, pay):
    art = signup(client, "a@example.com")
    ref = buy(client, art).json()["reference"]
    pay.succeed(ref, "5")                                                  # paid GH₵5 for a GH₵50 product
    assert verify(client, art, ref).json()["status"] == "failed"
    assert plan_of(client, art)["plan"] == "free"
    ref2 = buy(client, art).json()["reference"]
    pay.succeed(ref2, "50", currency="USD")
    assert verify(client, art, ref2).json()["status"] == "failed"
    assert plan_of(client, art)["plan"] == "free"


def test_failed_and_unreachable_provider_states(client, pay):
    art = signup(client, "a@example.com")
    ref = buy(client, art).json()["reference"]
    pay.unreachable = True
    assert verify(client, art, ref).json()["status"] == "pending"          # cannot tell, so keep waiting
    pay.unreachable = False
    pay.fail(ref)
    r = verify(client, art, ref).json()
    assert r["status"] == "failed" and "not been charged" in r["message"]
    pay.succeed(ref, "50")                                                 # a failed order cannot later be revived
    assert verify(client, art, ref).json()["status"] == "failed" and plan_of(client, art)["plan"] == "free"


# ------------------------------------------------------------------ webhook
def post_hook(client, body: dict, signature="valid"):
    raw = json.dumps(body).encode()
    sig = sign(raw) if signature == "valid" else signature
    return client.post("/api/billing/webhook/paystack", content=raw, headers={"x-paystack-signature": sig or ""})


def test_webhook_needs_valid_signature_and_still_double_checks_with_provider(client, pay):
    art = signup(client, "a@example.com")
    ref = buy(client, art).json()["reference"]
    body = {"event": "charge.success", "data": {"reference": ref}}
    assert post_hook(client, body, signature="deadbeef").status_code == 401
    assert post_hook(client, body, signature="").status_code == 401
    assert plan_of(client, art)["plan"] == "free"

    # a correctly signed message is NOT enough: the provider must confirm too
    assert post_hook(client, body).status_code == 200
    assert plan_of(client, art)["plan"] == "free"

    pay.succeed(ref, "50")
    assert post_hook(client, body).status_code == 200
    assert plan_of(client, art)["plan"] == "premium"
    assert post_hook(client, body).status_code == 200                      # Paystack retries: harmless
    with SessionLocal() as db:
        assert db.query(Subscription).count() == 1


def test_webhook_ignores_unknown_references_and_other_events(client, pay):
    assert post_hook(client, {"event": "charge.success", "data": {"reference": "FSW-DOESNOTEXIST"}}).status_code == 200
    assert post_hook(client, {"event": "transfer.success", "data": {}}).status_code == 200
    assert client.post("/api/billing/webhook/paystack", content=b"not json", headers={"x-paystack-signature": sign(b"not json")}).status_code == 400


def test_webhook_and_browser_callback_arriving_together_credit_once(client, pay):
    art = signup(client, "a@example.com")
    ref = buy(client, art).json()["reference"]
    pay.succeed(ref, "50")
    post_hook(client, {"event": "charge.success", "data": {"reference": ref}})
    verify(client, art, ref)
    with SessionLocal() as db:
        assert db.query(Subscription).count() == 1 and db.query(PaymentItem).filter(PaymentItem.fulfilled_at.is_not(None)).count() == 1


# -------------------------------------------------- subscriptions: renewal, expiry
def test_renewal_extends_instead_of_overlapping(client, pay):
    art = signup(client, "a@example.com")
    for _ in range(2):
        ref = buy(client, art).json()["reference"]
        pay.succeed(ref, "50")
        verify(client, art, ref)
    with SessionLocal() as db:
        subs = db.query(Subscription).order_by(Subscription.id).all()
        first_end, second_start, second_end = [s.ends_at.replace(tzinfo=None) for s in (subs[0], subs[1], subs[1])][0], subs[1].starts_at.replace(tzinfo=None), subs[1].ends_at.replace(tzinfo=None)
        assert abs((second_start - first_end).total_seconds()) < 5          # second period starts when the first ends
        assert 59 <= (second_end - datetime.now(timezone.utc).replace(tzinfo=None)).days <= 60


def test_expired_premium_drops_back_to_free_but_gifted_premium_stays(client, pay):
    adm = admin_headers(client)
    a = signup(client, "a@example.com")
    b = signup(client, "b@example.com", name="Yaw Boateng")
    ref = buy(client, a).json()["reference"]
    pay.succeed(ref, "50")
    verify(client, a, ref)
    client.post("/api/admin/artisans/2/plan", headers=adm, json={"plan": "premium"})          # complimentary, no subscription
    with SessionLocal() as db:
        db.execute(text("update subscriptions set ends_at = :t"), {"t": datetime.now(timezone.utc) - timedelta(days=1)}); db.commit()
    assert client.get("/api/artisans/1").json()["plan"] == "premium"                          # not yet processed
    with SessionLocal() as db:
        assert expire_due_subscriptions(db) == 1
        assert expire_due_subscriptions(db) == 0                                              # idempotent
    assert client.get("/api/artisans/1").json()["plan"] == "free"
    assert client.get("/api/artisans/2").json()["plan"] == "premium"                          # admin gift untouched
    assert "ended" in client.get("/api/notifications", headers=a).json()["items"][0]["title"]
    assert plan_of(client, a)["premium_until"] is None


# ------------------------------------------------------------- sponsored listings
def test_sponsored_listing_features_the_profile_for_a_limited_time(client, pay):
    art = signup(client, "a@example.com")
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 0
    ref = buy(client, art, "sponsored_7d").json()["reference"]
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 0                # not before payment
    pay.succeed(ref, "40")
    verify(client, art, ref)
    assert client.get("/api/artisans?featured_only=true").json()["total"] == 1
    me = plan_of(client, art)
    end = datetime.fromisoformat(me["sponsored_until"].replace("Z", "+00:00"))
    end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    assert 6 <= (end - datetime.now(timezone.utc)).days <= 7
    ref2 = buy(client, art, "sponsored_30d").json()["reference"]                              # buying more stacks on top
    pay.succeed(ref2, "120")
    verify(client, art, ref2)
    end2 = datetime.fromisoformat(plan_of(client, art)["sponsored_until"].replace("Z", "+00:00"))
    end2 = end2 if end2.tzinfo else end2.replace(tzinfo=timezone.utc)
    assert (end2 - end).days >= 29


def test_sponsoring_never_shortens_a_permanent_feature(client, pay):
    adm = admin_headers(client)
    art = signup(client, "a@example.com")
    client.post("/api/admin/artisans/1/feature", headers=adm, json={"featured": True})        # permanent
    ref = buy(client, art, "sponsored_7d").json()["reference"]
    pay.succeed(ref, "40")
    assert verify(client, art, ref).json()["status"] == "completed"
    with SessionLocal() as db:
        assert db.query(ArtisanProfile).one().featured_until is None


# ------------------------------------------------------------- paid verification
def png():
    import io
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (60, 40), (80, 80, 80)).save(b, "PNG")
    return b.getvalue()


def apply_verification(client, h):
    return client.post("/api/artisan/me/verification", headers=h, data={"id_type": "Ghana Card"}, files={"document": ("id.png", png(), "image/png")})


def test_verification_fee_must_be_paid_when_set_and_is_consumed_once(client, pay, monkeypatch):
    monkeypatch.setattr(get_settings(), "VERIFICATION_FEE_GHS", Decimal("25"))
    adm = admin_headers(client)
    art = signup(client, "a@example.com")
    assert apply_verification(client, art).status_code == 402                                 # must pay first
    assert any(p["code"] == "verification" and p["purchasable"] for p in client.get("/api/billing/plans").json()["products"])

    ref = buy(client, art, "verification").json()["reference"]
    assert apply_verification(client, art).status_code == 402                                 # paying is not enough until confirmed
    pay.succeed(ref, "25")
    assert verify(client, art, ref).json()["status"] == "completed"
    assert plan_of(client, art)["verification_credit"] is True
    assert buy(client, art, "verification").status_code == 409                                # no double-paying

    r = apply_verification(client, art)
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert plan_of(client, art)["verification_credit"] is False                               # credit used up
    vid = client.get("/api/admin/verifications", headers=adm).json()["items"][0]["id"]
    client.post(f"/api/admin/verifications/{vid}/decision", headers=adm, json={"approve": False, "note": "Blurry photo"})
    assert apply_verification(client, art).status_code == 402                                 # a new application needs a new fee


def test_verification_stays_free_while_payments_are_off(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "VERIFICATION_FEE_GHS", Decimal("25"))                # fee set but no provider configured
    art = signup(client, "a@example.com")
    assert apply_verification(client, art).status_code == 201                                 # never blocks on an impossible payment


# ---------------------------------------------------------------- admin view
def test_admin_sees_payments_and_revenue_but_cannot_mark_paid(client, pay):
    adm = admin_headers(client)
    a = signup(client, "a@example.com")
    paid = buy(client, a).json()["reference"]
    buy(client, a, "sponsored_7d")                                                            # left unpaid
    pay.succeed(paid, "50")
    verify(client, a, paid)

    assert client.get("/api/admin/payments", headers=a).status_code == 403
    r = client.get("/api/admin/payments", headers=adm).json()
    assert r["total"] == 2 and Decimal(r["revenue_ghs"]) == 50 and r["completed_count"] == 1       # only confirmed money counts
    assert client.get("/api/admin/payments?status=pending", headers=adm).json()["total"] == 1
    assert client.get("/api/admin/payments?purpose=subscription", headers=adm).json()["items"][0]["user_email"] == "a@example.com"
    s = client.get("/api/admin/stats", headers=adm).json()
    assert Decimal(s["revenue_ghs"]) == 50 and s["payments_pending"] == 1 and s["active_premium"] == 1
    assert client.post("/api/admin/payments/1/complete", headers=adm).status_code in (404, 405)    # no such power exists


# --------------------------------------------------------- the real Paystack adapter
def fake_http(monkeypatch, responses):
    calls = []

    def request(method, url, **kw):
        calls.append((method, url, kw))
        status, body = responses.pop(0)
        return httpx.Response(status, json=body, request=httpx.Request(method, url))

    monkeypatch.setattr("services.payments.paystack.httpx.request", request)
    return calls


def test_paystack_adapter_builds_correct_requests(monkeypatch):
    p = PaystackProvider("sk_test_abc", "https://api.paystack.co/")
    calls = fake_http(monkeypatch, [(200, {"status": True, "data": {"authorization_url": "https://checkout.paystack.com/x", "access_code": "ac1"}})])
    s = p.initialize(reference="FSW-1", email="a@example.com", amount=Decimal("49.99"), currency="GHS",
                     callback_url="https://site/billing/callback", channel="mobile_money", metadata={"product": "premium_monthly"})
    method, url, kw = calls[0]
    assert (method, url) == ("POST", "https://api.paystack.co/transaction/initialize")
    assert kw["headers"]["Authorization"] == "Bearer sk_test_abc"
    assert kw["json"]["amount"] == 4999 and isinstance(kw["json"]["amount"], int)             # pesewas, as an integer
    assert kw["json"]["channels"] == ["mobile_money"] and kw["json"]["currency"] == "GHS" and kw["json"]["reference"] == "FSW-1"
    assert s.authorization_url == "https://checkout.paystack.com/x"


def test_paystack_adapter_maps_statuses_and_errors(monkeypatch):
    p = PaystackProvider("sk_test_abc", "https://api.paystack.co")
    ok = {"status": True, "data": {"status": "success", "amount": 5000, "currency": "GHS", "reference": "R1", "channel": "mobile_money"}}
    fake_http(monkeypatch, [(200, ok)])
    c = p.verify("R1")
    assert (c.status, c.amount, c.currency, c.reference) == ("success", Decimal("50"), "GHS", "R1")
    for raw, mapped in (("failed", "failed"), ("reversed", "failed"), ("abandoned", "pending"), ("ongoing", "pending")):
        fake_http(monkeypatch, [(200, {"status": True, "data": {"status": raw, "amount": 0, "currency": "GHS", "reference": "R"}})])
        assert p.verify("R").status == mapped
    fake_http(monkeypatch, [(401, {"status": False, "message": "Invalid key"})])
    with pytest.raises(PaymentProviderError, match="Invalid key"):
        p.verify("R")

    def boom(*a, **k):
        raise httpx.ConnectError("network down")
    monkeypatch.setattr("services.payments.paystack.httpx.request", boom)
    with pytest.raises(PaymentProviderError, match="Could not reach"):
        p.verify("R")


def test_paystack_webhook_signature_is_hmac_sha512():
    p = PaystackProvider("sk_test_abc", "https://api.paystack.co")
    import hashlib, hmac
    body = b'{"event":"charge.success"}'
    good = hmac.new(b"sk_test_abc", body, hashlib.sha512).hexdigest()
    assert p.valid_webhook_signature(body, good) and p.valid_webhook_signature(body, good.upper())
    assert not p.valid_webhook_signature(body, good[:-1] + "0") and not p.valid_webhook_signature(body, None)
    assert not p.valid_webhook_signature(b'{"event":"charge.success","x":1}', good)               # body tampering detected


# --------------------------------------------------- production safety and misc
def test_production_refuses_unsafe_settings():
    good = dict(ENVIRONMENT="production", DATABASE_URL="postgresql+psycopg2://u:p@db/app", SECRET_KEY="k" * 48,
                CORS_ORIGINS="https://example.com", FRONTEND_URL="https://example.com")
    assert Settings(_env_file=None, **good).docs_enabled is False
    for bad in ({"DATABASE_URL": "sqlite:///./x.db"}, {"CORS_ORIGINS": "http://example.com"}, {"FRONTEND_URL": "http://example.com"},
                {"SECRET_KEY": "replace-with-a-long-random-string-xxxxxxxxxx"}):
        with pytest.raises(ValueError, match="Unsafe production configuration"):
            Settings(_env_file=None, **{**good, **bad})
    assert Settings(_env_file=None, ENVIRONMENT="development", SECRET_KEY="k" * 48).docs_enabled is True


def test_security_headers_and_readiness(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert client.get("/api/health/ready").json() == {"status": "ready"}


def test_remove_demo_cleans_everything_without_foreign_key_errors(client):
    import seed
    with SessionLocal() as db:
        seed.seed_categories(db)
        seed.seed_demo(db)
    cust = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": "customer.demo@example.com", "password": "Demo1234"}).json()["access_token"]}
    art = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": "kwame.demo@example.com", "password": "Demo1234"}).json()["access_token"]}
    rid = client.post("/api/requests", headers=cust, data={"artisan_id": 1, "title": "Leaking sink", "description": "Water under the sink.", "location": "Madina"}).json()["id"]
    for st in ("accepted", "in_progress", "completed"):
        client.patch(f"/api/requests/{rid}/status", headers=art, json={"status": st})
    client.post(f"/api/requests/{rid}/review", headers=cust, json={"rating": 5, "comment": "Great"})
    real = signup(client, "real@example.com", role="customer", name="Real Person")
    with SessionLocal() as db:
        seed.remove_demo(db)
        assert db.query(User).filter(User.email.like("%.demo@example.com")).count() == 0
        assert db.query(User).filter(User.email == "real@example.com").count() == 1             # real accounts untouched
    assert client.get("/api/auth/me", headers=real).status_code == 200
    assert client.get("/api/artisans").json()["total"] == 0
