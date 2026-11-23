import logging
import secrets
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import get_db
from dependencies import get_current_user
from models import (
    ArtisanLocation, ArtisanPortfolio, ArtisanProfile, ContactMessage, Notification,
    RequestPhoto, RequestStatus, Review, ServiceCategory, ServiceRequest,
    PlanType, Subscription, SubscriptionStatus, User, UserRole, Verification, VerificationStatus,
)
from schemas import ChangePasswordRequest, DeleteAccountRequest, LoginRequest, MeOut, RegisterRequest, TokenOut
from services import rate_limit
from services.uploads import delete_image

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


def _login(db: Session, email: str, password: str, request: Request) -> User:
    key = f"{request.client.host if request.client else 'unknown'}:{email}"
    if rate_limit.is_blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in 15 minutes.")
    user = db.query(User).filter(User.email == email).first()
    if not verify_password(password, user.password_hash if user else None):
        rate_limit.record_failure(key)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is deactivated")
    if user.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been suspended. Please contact support.")
    rate_limit.reset(key)
    return user


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    category = None
    if data.role == UserRole.artisan:
        category = db.get(ServiceCategory, data.category_id)
        if category is None or not category.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Selected occupation does not exist")

    user = User(
        full_name=data.full_name, email=data.email, phone=data.phone,
        password_hash=hash_password(data.password), role=data.role,
    )
    db.add(user)
    db.flush()

    if category is not None:
        profile = ArtisanProfile(user_id=user.id, category_id=category.id, phone=data.phone, whatsapp_number=data.phone)
        if data.location:
            profile.locations.append(ArtisanLocation(location=data.location.strip().title()))
        db.add(profile)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _login(db, data.email, data.password, request)
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)


@router.post("/token", include_in_schema=True, summary="OAuth2 form login (used by the Swagger 'Authorize' button)")
def token(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _login(db, form.username.lower(), form.password, request)
    return {"access_token": create_access_token(user.id, user.role.value), "token_type": "bearer"}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    data: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently disable and anonymise a customer/artisan account.

    Historical requests and payment ledger rows are retained in anonymised form so
    existing job/payment records remain internally consistent. Profile media and
    user-authored request attachments are removed where possible.
    """
    if user.role == UserRole.admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Administrator accounts cannot be deleted from the customer dashboard. Contact the platform owner.",
        )

    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect")

    old_email = user.email
    media_to_delete: list[str] = []

    # Remove the account holder's own service-request attachments and redact
    # identifying details, while preserving the job record for the other party.
    customer_requests = db.query(ServiceRequest).filter(ServiceRequest.customer_id == user.id).all()
    for service_request in customer_requests:
        for photo in list(service_request.photos):
            if photo.image_path:
                media_to_delete.append(photo.image_path)
            db.delete(photo)
        service_request.title = "Request from deleted account"
        service_request.description = "Details removed because the customer deleted their account."
        service_request.location = "Removed"
        service_request.preferred_date = None
        service_request.status_note = "Customer account deleted"
        if service_request.status in (RequestStatus.pending, RequestStatus.accepted, RequestStatus.in_progress):
            service_request.status = RequestStatus.cancelled

    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is not None:
        # Stop new customer discovery and prevent further use of the public listing.
        profile.is_available = False
        profile.is_featured = False
        profile.featured_until = None
        profile.headline = None
        profile.bio = None
        profile.phone = None
        profile.whatsapp_number = None
        profile.price_min = None
        profile.price_max = None
        profile.price_note = None
        if profile.profile_image:
            media_to_delete.append(profile.profile_image)
        profile.profile_image = None
        profile.years_experience = 0
        profile.verification_status = VerificationStatus.unverified
        profile.plan = PlanType.free
        profile.locations.clear()

        for portfolio_item in db.query(ArtisanPortfolio).filter(ArtisanPortfolio.artisan_id == profile.id).all():
            media_to_delete.append(portfolio_item.image_path)
            db.delete(portfolio_item)

        for verification in db.query(Verification).filter(Verification.artisan_id == profile.id).all():
            media_to_delete.append(verification.document_path)
            if verification.trade_certificate_path:
                media_to_delete.append(verification.trade_certificate_path)
            db.delete(verification)

        # Existing requests remain as history, but active work is closed because
        # this artisan will no longer be available on the platform.
        artisan_requests = db.query(ServiceRequest).filter(ServiceRequest.artisan_id == profile.id).all()
        for service_request in artisan_requests:
            if service_request.status in (RequestStatus.pending, RequestStatus.accepted, RequestStatus.in_progress):
                service_request.status = RequestStatus.cancelled
                service_request.status_note = "Artisan account deleted"

    # Remove reviews written by this customer and refresh the affected artisans'
    # aggregate scores. Reviews received by a deleted artisan remain attached to
    # the anonymised, non-public historical profile.
    affected_artisan_ids = set()
    authored_reviews = db.query(Review).filter(Review.customer_id == user.id).all()
    for review in authored_reviews:
        affected_artisan_ids.add(review.artisan_id)
        db.delete(review)

    for artisan_id in affected_artisan_ids:
        artisan = db.get(ArtisanProfile, artisan_id)
        if artisan is not None:
            avg_rating, review_count = db.query(func.avg(Review.rating), func.count(Review.id)).filter(
                Review.artisan_id == artisan_id
            ).one()
            artisan.avg_rating = round(Decimal(str(avg_rating or 0)), 2)
            artisan.review_count = review_count or 0

    # Cancel internal subscriptions, but preserve payment rows as financial records.
    for subscription in db.query(Subscription).filter(Subscription.user_id == user.id).all():
        if subscription.status in (SubscriptionStatus.pending, SubscriptionStatus.active):
            subscription.status = SubscriptionStatus.cancelled

    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(ContactMessage).filter(ContactMessage.email == old_email).delete(synchronize_session=False)

    # Replace account identifiers and credentials so personal data is no longer
    # available through the application and the old login/session cannot be used.
    user.full_name = "Deleted account"
    user.email = f"deleted-{uuid4().hex}@deleted.invalid"
    user.phone = None
    user.password_hash = hash_password(secrets.token_urlsafe(48))
    user.is_active = False
    user.is_suspended = False
    user.suspended_reason = None

    db.commit()

    # Remove external/local media after the database transaction succeeds. A
    # storage outage must not roll back account deletion; record cleanup failures.
    for media_path in set(filter(None, media_to_delete)):
        try:
            delete_image(media_path)
        except Exception:
            logger.exception("Account deletion media cleanup failed for user_id=%s", user.id)

    return None
