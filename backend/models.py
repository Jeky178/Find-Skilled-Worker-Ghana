import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _enum(e: type[enum.Enum]) -> Enum:
    # Stored as VARCHAR (not a native PG enum) so migrations stay simple.
    return Enum(e, native_enum=False, length=30, values_callable=lambda x: [m.value for m in x])


# ----------------------------------------------------------------- enums
class UserRole(str, enum.Enum):
    customer = "customer"
    artisan = "artisan"
    admin = "admin"


class VerificationStatus(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PlanType(str, enum.Enum):
    free = "free"
    premium = "premium"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class ReportStatus(str, enum.Enum):
    open = "open"
    reviewing = "reviewing"
    resolved = "resolved"
    dismissed = "dismissed"


class SubscriptionStatus(str, enum.Enum):
    pending = "pending"      # created, awaiting a confirmed payment
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"      # NEVER set to completed without provider confirmation
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentPurpose(str, enum.Enum):
    subscription = "subscription"
    verification = "verification"
    sponsored_listing = "sponsored_listing"
    business_subscription = "business_subscription"


# ----------------------------------------------------------------- mixin
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ----------------------------------------------------------------- models
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # stored lower-case
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.customer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    suspended_reason: Mapped[str | None] = mapped_column(String(500))

    artisan_profile: Mapped["ArtisanProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    requests: Mapped[list["ServiceRequest"]] = relationship(
        back_populates="customer", foreign_keys="ServiceRequest.customer_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ServiceCategory(TimestampMixin, Base):
    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(300))
    icon: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    artisans: Mapped[list["ArtisanProfile"]] = relationship(back_populates="category")


class ArtisanProfile(TimestampMixin, Base):
    __tablename__ = "artisan_profiles"
    __table_args__ = (
        CheckConstraint("years_experience >= 0 AND years_experience <= 60", name="ck_artisan_experience"),
        CheckConstraint("price_min IS NULL OR price_min >= 0", name="ck_artisan_price_min"),
        CheckConstraint("price_max IS NULL OR price_min IS NULL OR price_max >= price_min", name="ck_artisan_price_range"),
        Index("ix_artisan_listing", "category_id", "is_available", "verification_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.id"), index=True)
    headline: Mapped[str | None] = mapped_column(String(150))
    bio: Mapped[str | None] = mapped_column(Text)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))  # international format, digits only
    profile_image: Mapped[str | None] = mapped_column(String(255))
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_note: Mapped[str | None] = mapped_column(String(200))  # e.g. "Per visit", "Quote after inspection"
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        _enum(VerificationStatus), default=VerificationStatus.unverified
    )
    plan: Mapped[PlanType] = mapped_column(_enum(PlanType), default=PlanType.free)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    featured_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Denormalised review stats, recomputed whenever a review is added.
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="artisan_profile")
    category: Mapped["ServiceCategory"] = relationship(back_populates="artisans")
    locations: Mapped[list["ArtisanLocation"]] = relationship(back_populates="artisan", cascade="all, delete-orphan")
    portfolio: Mapped[list["ArtisanPortfolio"]] = relationship(back_populates="artisan", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="artisan")
    requests: Mapped[list["ServiceRequest"]] = relationship(back_populates="artisan")
    verifications: Mapped[list["Verification"]] = relationship(back_populates="artisan", cascade="all, delete-orphan")


class ArtisanLocation(Base):
    """Areas an artisan serves (e.g. Madina, Dome). One row per area, so filtering is indexed."""
    __tablename__ = "artisan_locations"
    __table_args__ = (UniqueConstraint("artisan_id", "location", name="uq_artisan_location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    location: Mapped[str] = mapped_column(String(80), index=True)

    artisan: Mapped["ArtisanProfile"] = relationship(back_populates="locations")


class ArtisanPortfolio(TimestampMixin, Base):
    __tablename__ = "artisan_portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(String(200))

    artisan: Mapped["ArtisanProfile"] = relationship(back_populates="portfolio")


class ServiceRequest(TimestampMixin, Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint("length(title) >= 3", name="ck_request_title_len"),
        Index("ix_request_artisan_status", "artisan_id", "status"),
        Index("ix_request_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisan_profiles.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.id"))
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(120))
    preferred_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RequestStatus] = mapped_column(_enum(RequestStatus), default=RequestStatus.pending)
    status_note: Mapped[str | None] = mapped_column(String(500))  # e.g. reason for rejection

    customer: Mapped["User"] = relationship(back_populates="requests", foreign_keys=[customer_id])
    artisan: Mapped["ArtisanProfile"] = relationship(back_populates="requests")
    category: Mapped["ServiceCategory"] = relationship()
    photos: Mapped[list["RequestPhoto"]] = relationship(back_populates="request", cascade="all, delete-orphan")
    review: Mapped["Review | None"] = relationship(back_populates="request", uselist=False)


class RequestPhoto(Base):
    __tablename__ = "request_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"), index=True)
    image_path: Mapped[str] = mapped_column(String(255))

    request: Mapped["ServiceRequest"] = relationship(back_populates="photos")


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        UniqueConstraint("request_id", name="uq_review_request"),  # one review per completed job
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisan_profiles.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)

    request: Mapped["ServiceRequest"] = relationship(back_populates="review")
    customer: Mapped["User"] = relationship()
    artisan: Mapped["ArtisanProfile"] = relationship(back_populates="reviews")


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_user_read", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(255))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="notifications")


class Verification(TimestampMixin, Base):
    """An artisan's application for the verified badge. Reviewed manually by an admin."""
    __tablename__ = "verifications"
    __table_args__ = (Index("ix_verification_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    artisan_id: Mapped[int] = mapped_column(ForeignKey("artisan_profiles.id", ondelete="CASCADE"), index=True)
    id_type: Mapped[str] = mapped_column(String(40))          # e.g. "Ghana Card", "Driver's Licence"
    document_path: Mapped[str] = mapped_column(String(255))   # uploaded ID photo (private)
    trade_certificate_path: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[VerificationStatus] = mapped_column(_enum(VerificationStatus), default=VerificationStatus.pending)
    admin_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    artisan: Mapped["ArtisanProfile"] = relationship(back_populates="verifications")
    reviewed_by: Mapped["User | None"] = relationship()


class Report(TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("reporter_id <> reported_user_id", name="ck_report_not_self"),
        Index("ix_report_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reported_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("service_requests.id"))
    reason: Mapped[str] = mapped_column(String(100))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(_enum(ReportStatus), default=ReportStatus.open)
    admin_note: Mapped[str | None] = mapped_column(String(500))
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])
    reported_user: Mapped["User"] = relationship(foreign_keys=[reported_user_id])
    resolved_by: Mapped["User | None"] = relationship(foreign_keys=[resolved_by_id])


# ------------------------------------------------- monetisation (architecture only)
class Subscription(TimestampMixin, Base):
    """
    A premium/business plan. Stays `pending` until a payment is confirmed by a
    configured provider (Paystack / Mobile Money). Nothing activates it automatically.
    """
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscription_user_status", "user_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan: Mapped[PlanType] = mapped_column(_enum(PlanType))
    status: Mapped[SubscriptionStatus] = mapped_column(_enum(SubscriptionStatus), default=SubscriptionStatus.pending)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payment_amount"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(_enum(PaymentPurpose))
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="GHS")
    provider: Mapped[str | None] = mapped_column(String(30))              # "paystack", "mtn_momo", ...
    reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[PaymentStatus] = mapped_column(_enum(PaymentStatus), default=PaymentStatus.pending)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship()


class ContactMessage(TimestampMixin, Base):
    """Messages sent from the public Contact page. Read by admins."""
    __tablename__ = "contact_messages"
    __table_args__ = (Index("ix_contact_unread", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    topic: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class AdminAction(Base):
    """Audit trail: who (an admin) did what, and to whom. Never edited or deleted by the app."""
    __tablename__ = "admin_actions"
    __table_args__ = (Index("ix_admin_actions_created", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str] = mapped_column(String(30))
    target_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    admin: Mapped["User"] = relationship()


class PaymentItem(TimestampMixin, Base):
    """
    What a payment buys, and whether it has been delivered.

    `fulfilled_at` is set exactly once, in the same transaction that delivers the product
    (activates Premium, grants a verification credit, sponsors a listing). That makes
    fulfilment idempotent: a webhook and a browser callback can arrive together and the
    artisan is still only credited once.
    """
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True)
    product_code: Mapped[str] = mapped_column(String(40), index=True)
    artisan_id: Mapped[int | None] = mapped_column(ForeignKey("artisan_profiles.id"))
    period_days: Mapped[int] = mapped_column(Integer, default=0)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))   # verification credit used
    target_id: Mapped[int | None] = mapped_column(Integer)                           # subscription / verification id
    note: Mapped[str | None] = mapped_column(String(200))

    payment: Mapped["Payment"] = relationship()
