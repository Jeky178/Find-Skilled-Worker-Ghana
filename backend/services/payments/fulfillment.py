"""
Delivering what was paid for. Runs ONLY after the provider has confirmed the money arrived.
Safe to call any number of times for the same payment (idempotent).
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from models import (
    ArtisanProfile, Payment, PaymentItem, PaymentStatus, PlanType, Subscription, SubscriptionStatus,
)
from services.notifications import notify
from services.payments.base import VerifiedCharge

log = logging.getLogger("fsw.payments")


def _utc(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def charge_matches(payment: Payment, charge: VerifiedCharge) -> bool:
    """A successful charge only counts if reference, amount and currency are exactly what we asked for."""
    return charge.status == "success" and charge.reference == payment.reference and charge.currency == payment.currency and charge.amount == payment.amount


def mark_failed(db: Session, payment: Payment, why: str) -> None:
    if payment.status == PaymentStatus.pending:
        payment.status = PaymentStatus.failed
        log.warning("payment %s failed: %s", payment.reference, why)


def fulfill(db: Session, payment: Payment, paid_at: datetime | None = None) -> bool:
    """Mark the payment completed and deliver the product. Returns True if it delivered now, False if already done."""
    item = db.query(PaymentItem).filter(PaymentItem.payment_id == payment.id).with_for_update().one()
    if item.fulfilled_at is not None:
        return False

    now = datetime.now(timezone.utc)
    payment.status, payment.paid_at = PaymentStatus.completed, paid_at or now
    artisan = db.query(ArtisanProfile).options(joinedload(ArtisanProfile.user)).filter(ArtisanProfile.id == item.artisan_id).first()
    code = item.product_code

    if code.startswith("premium") and artisan:
        current = (db.query(Subscription).filter(Subscription.user_id == payment.user_id, Subscription.status == SubscriptionStatus.active)
                   .order_by(Subscription.ends_at.desc()).first())
        start = max(now, _utc(current.ends_at)) if current and current.ends_at else now      # renewing extends, never overlaps
        sub = Subscription(user_id=payment.user_id, plan=PlanType.premium, status=SubscriptionStatus.active,
                           starts_at=start, ends_at=start + timedelta(days=item.period_days))
        db.add(sub)
        db.flush()
        payment.subscription_id, item.target_id = sub.id, sub.id
        artisan.plan = PlanType.premium
        notify(db, payment.user_id, "Premium is active", f"Thank you. Your Premium plan runs until {sub.ends_at:%d %b %Y}.", "/dashboard/billing")
    elif code == "verification":
        notify(db, payment.user_id, "Verification fee received", "Thank you. You can now submit your documents for verification.", "/dashboard/verification")
    elif code.startswith("sponsored") and artisan:
        permanent = artisan.is_featured and artisan.featured_until is None
        if permanent:
            item.note = "Already featured permanently; no change made"
        else:
            active = artisan.is_featured and artisan.featured_until and _utc(artisan.featured_until) > now
            start = _utc(artisan.featured_until) if active else now
            artisan.is_featured, artisan.featured_until = True, start + timedelta(days=item.period_days)
            notify(db, payment.user_id, "Your listing is sponsored", f"Your profile is featured until {artisan.featured_until:%d %b %Y}.", "/dashboard/billing")

    item.fulfilled_at = now
    log.info("payment %s completed and fulfilled (%s)", payment.reference, code)
    return True


def expire_due_subscriptions(db: Session) -> int:
    """Move finished Premium subscriptions to 'expired' and drop the artisan back to Free. Returns how many expired."""
    now = datetime.now(timezone.utc)
    due = db.query(Subscription).filter(Subscription.status == SubscriptionStatus.active, Subscription.ends_at <= now).all()
    for sub in due:
        sub.status = SubscriptionStatus.expired
        still_active = (db.query(Subscription.id).filter(Subscription.user_id == sub.user_id, Subscription.status == SubscriptionStatus.active,
                                                         Subscription.ends_at > now, Subscription.id != sub.id).first())
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == sub.user_id).first()
        if profile and not still_active and profile.plan == PlanType.premium:
            profile.plan = PlanType.free
            notify(db, sub.user_id, "Your Premium plan has ended", "Your profile is back on the Free plan. You can renew any time.", "/dashboard/billing")
    if due:
        db.commit()
        log.info("expired %d subscription(s)", len(due))
    return len(due)


def verification_credit(db: Session, user_id: int) -> PaymentItem | None:
    """A paid verification fee that has not been used for an application yet."""
    return (db.query(PaymentItem).join(Payment, Payment.id == PaymentItem.payment_id)
            .filter(Payment.user_id == user_id, PaymentItem.product_code == "verification",
                    PaymentItem.fulfilled_at.is_not(None), PaymentItem.consumed_at.is_(None)).first())
