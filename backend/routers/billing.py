"""Plans, checkout and payment confirmation. No money is ever marked as received without the provider confirming it."""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from config import get_settings
from database import get_db
from dependencies import require_artisan
from models import (
    ArtisanProfile, Payment, PaymentItem, PaymentStatus, PlanType, Subscription, SubscriptionStatus, User, VerificationStatus,
)
from schemas_billing import BillingMeOut, CheckoutIn, CheckoutOut, PaymentOut, PlansOut, ProductOut, VerifyOut
from services.payments.base import PaymentProviderError
from services.payments.fulfillment import charge_matches, fulfill, mark_failed, verification_credit
from services.payments.paystack import get_provider
from services.pricing import catalog, get_product

router = APIRouter(prefix="/api/billing", tags=["Billing and payments"])
log = logging.getLogger("fsw.payments")
settings = get_settings()

CURRENCY = "GHS"
NOT_AVAILABLE = "Online payments are not switched on yet. Please check back soon."


def _own_profile(user: User, db: Session) -> ArtisanProfile:
    p = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan profile not found")
    return p


@router.get("/plans", response_model=PlansOut)
def plans():
    """The public price list. `purchasable` is false for anything that cannot be bought right now."""
    products = [
        ProductOut(code=p.code, name=p.name, description=p.description, price_ghs=p.price, period_days=p.period_days,
                   purchasable=p.purchasable and settings.payments_enabled, coming_soon=not p.available)
        for p in catalog()
    ]
    return PlansOut(payments_enabled=settings.payments_enabled, currency=CURRENCY, products=products)


@router.get("/me", response_model=BillingMeOut)
def my_billing(user: User = Depends(require_artisan), db: Session = Depends(get_db)):
    p = _own_profile(user, db)
    now = datetime.now(timezone.utc)
    sub = (db.query(Subscription).filter(Subscription.user_id == user.id, Subscription.status == SubscriptionStatus.active, Subscription.ends_at > now)
           .order_by(Subscription.ends_at.desc()).first())
    return BillingMeOut(
        plan=p.plan, premium_until=sub.ends_at if sub else None,
        sponsored_until=p.featured_until if p.is_featured and p.featured_until else None,
        payments_enabled=settings.payments_enabled, verification_status=p.verification_status,
        verification_fee_ghs=settings.VERIFICATION_FEE_GHS, verification_credit=verification_credit(db, user.id) is not None,
    )


@router.post("/checkout", response_model=CheckoutOut, status_code=status.HTTP_201_CREATED)
def checkout(data: CheckoutIn, user: User = Depends(require_artisan), db: Session = Depends(get_db)):
    provider = get_provider()
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_AVAILABLE)
    product = get_product(data.product_code)
    if product is None or not product.purchasable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That product is not available")

    profile = _own_profile(user, db)
    if product.code == "verification":
        if profile.verification_status in (VerificationStatus.approved, VerificationStatus.pending):
            raise HTTPException(status.HTTP_409_CONFLICT, "You are already verified or your application is being reviewed")
        if verification_credit(db, user.id) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "You have already paid the verification fee. Submit your documents")

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    if db.query(func.count(Payment.id)).filter(Payment.user_id == user.id, Payment.created_at >= since).scalar() >= 10:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many payment attempts. Please wait a while and try again")

    reference = f"FSW-{uuid.uuid4().hex[:20].upper()}"
    payment = Payment(user_id=user.id, purpose=product.purpose, amount=product.price, currency=CURRENCY, provider=provider.name,
                      reference=reference, status=PaymentStatus.pending)
    db.add(payment)
    db.flush()
    db.add(PaymentItem(payment_id=payment.id, product_code=product.code, artisan_id=profile.id, period_days=product.period_days))
    db.commit()                                               # keep our record even if the provider call fails

    try:
        session = provider.initialize(reference=reference, email=user.email, amount=product.price, currency=CURRENCY,
                                      callback_url=f"{settings.FRONTEND_URL.rstrip('/')}/billing/callback", channel=data.channel,
                                      metadata={"product": product.code, "user_id": user.id})
    except PaymentProviderError as exc:
        mark_failed(db, payment, str(exc))
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))
    return CheckoutOut(reference=reference, authorization_url=session.authorization_url)


def settle(db: Session, payment: Payment) -> str:
    """Ask the provider what really happened and act on the answer. Returns completed | pending | failed."""
    if payment.status == PaymentStatus.completed:
        return "completed"
    if payment.status == PaymentStatus.failed:
        return "failed"
    provider = get_provider()
    if provider is None:
        return "pending"
    try:
        charge = provider.verify(payment.reference)
    except PaymentProviderError:
        return "pending"                                       # cannot tell right now; try again later
    if charge.status == "success":
        if charge_matches(payment, charge):
            fulfill(db, payment, datetime.now(timezone.utc))
            db.commit()
            return "completed"
        log.error("payment %s: provider says success but amount/currency differ (%s %s vs %s %s). NOT fulfilled",
                  payment.reference, charge.amount, charge.currency, payment.amount, payment.currency)
        mark_failed(db, payment, "amount or currency mismatch")
        db.commit()
        return "failed"
    if charge.status == "failed":
        mark_failed(db, payment, "provider reported failure")
        db.commit()
        return "failed"
    return "pending"


_MESSAGES = {
    "completed": "Payment confirmed. Thank you.",
    "pending": "We have not received confirmation yet. If you completed the payment, check again in a minute.",
    "failed": "The payment was not completed. You have not been charged for this order.",
}


@router.get("/verify/{reference}", response_model=VerifyOut)
def verify_payment(reference: str, user: User = Depends(require_artisan), db: Session = Depends(get_db)):
    """Called when the customer returns from the payment page. Safe to call repeatedly."""
    payment = db.query(Payment).filter(Payment.reference == reference, Payment.user_id == user.id).first()
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment not found")
    result = settle(db, payment)
    item = db.query(PaymentItem).filter(PaymentItem.payment_id == payment.id).one()
    return VerifyOut(reference=reference, status=result, product_code=item.product_code, message=_MESSAGES[result])


@router.get("/history", response_model=list[PaymentOut])
def history(user: User = Depends(require_artisan), db: Session = Depends(get_db)):
    rows = (db.query(Payment, PaymentItem).join(PaymentItem, PaymentItem.payment_id == Payment.id)
            .filter(Payment.user_id == user.id).order_by(Payment.created_at.desc(), Payment.id.desc()).limit(50).all())
    names = {p.code: p.name for p in catalog()}
    return [PaymentOut(reference=p.reference, product_code=i.product_code, product_name=names.get(i.product_code, i.product_code),
                       amount=p.amount, currency=p.currency, status=p.status, created_at=p.created_at, paid_at=p.paid_at,
                       fulfilled=i.fulfilled_at is not None) for p, i in rows]


@router.post("/webhook/paystack", include_in_schema=True)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Paystack calls this when a payment succeeds. We check the signature, then still ask Paystack's API
    to confirm before delivering anything, so a forged or replayed message cannot give anyone Premium.
    """
    provider = get_provider()
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_AVAILABLE)
    raw = await request.body()
    if not provider.valid_webhook_signature(raw, request.headers.get("x-paystack-signature")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
    try:
        event = json.loads(raw)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid payload")
    if event.get("event") == "charge.success":
        reference = (event.get("data") or {}).get("reference")
        payment = db.query(Payment).filter(Payment.reference == reference).first() if reference else None
        if payment is not None:
            await run_in_threadpool(settle, db, payment)
    return {"received": True}                                  # always 200 for valid signatures so Paystack stops retrying
