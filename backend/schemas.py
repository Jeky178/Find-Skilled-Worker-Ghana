import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from models import PlanType, UserRole, VerificationStatus


def normalize_gh_phone(value: str | None) -> str | None:
    """Accepts 024xxxxxxx, +233 24 xxx xxxx, 233xxxxxxxxx. Returns '233XXXXXXXXX' (WhatsApp wa.me format)."""
    if value is None or value.strip() == "":
        return None
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "233" + digits[1:]
    if not re.fullmatch(r"233\d{9}", digits):
        raise ValueError("Enter a valid Ghana phone number, e.g. 0241234567 or +233241234567")
    return digits


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.customer
    # Required when registering as an artisan:
    category_id: int | None = None
    location: str | None = Field(default=None, max_length=80)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        return normalize_gh_phone(v)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain at least one letter and one number")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long")
        return v

    @model_validator(mode="after")
    def check_role(self):
        if self.role == UserRole.admin:
            raise ValueError("Administrator accounts cannot be self-registered")
        if self.role == UserRole.artisan and self.category_id is None:
            raise ValueError("Artisans must choose an occupation (category_id)")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class ArtisanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    verification_status: VerificationStatus
    plan: PlanType


class MeOut(UserOut):
    artisan_profile: ArtisanSummary | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut


class DeleteAccountRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    confirmation: str = Field(min_length=1, max_length=10)

    @field_validator("confirmation")
    @classmethod
    def confirm_permanent_deletion(cls, value: str) -> str:
        if value != "DELETE":
            raise ValueError('Type DELETE to confirm account deletion')
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return RegisterRequest.strong_password(v)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None


CONTACT_TOPICS = ["General question", "I need a worker", "I am an artisan", "Report a problem", "Partnership or advertising"]


class ContactMessageIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    topic: str
    message: str = Field(min_length=10, max_length=3000)

    @field_validator("name", "message")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        return normalize_gh_phone(v)

    @field_validator("topic")
    @classmethod
    def valid_topic(cls, v: str) -> str:
        if v not in CONTACT_TOPICS:
            raise ValueError("Please choose a topic from the list")
        return v


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str | None
    topic: str
    message: str
    is_read: bool
    created_at: datetime


# ------------------------------------------------------------------ artisans
from decimal import Decimal  # noqa: E402


class CategoryMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    icon: str | None


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    caption: str | None


class ArtisanCardOut(BaseModel):
    id: int
    name: str
    headline: str | None
    category: CategoryMini
    profile_image: str | None
    locations: list[str]
    price_min: Decimal | None
    price_max: Decimal | None
    price_note: str | None
    avg_rating: Decimal
    review_count: int
    years_experience: int
    is_available: bool
    verification_status: VerificationStatus
    plan: PlanType
    is_featured: bool


class ArtisanDetailOut(ArtisanCardOut):
    bio: str | None
    phone: str | None
    whatsapp_url: str | None
    portfolio: list[PortfolioOut]
    member_since: datetime


class ArtisanListOut(BaseModel):
    items: list[ArtisanCardOut]
    total: int
    page: int
    pages: int


class LocationCount(BaseModel):
    location: str
    count: int


class MyProfileOut(ArtisanDetailOut):
    category_id: int
    whatsapp_number: str | None
    completeness: int
    missing: list[str]
    portfolio_limit: int


class ProfileUpdate(BaseModel):
    """Every field is optional: only the ones sent are changed."""
    category_id: int | None = None
    headline: str | None = Field(default=None, max_length=150)
    bio: str | None = Field(default=None, max_length=2000)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    phone: str | None = None
    whatsapp_number: str | None = None
    price_min: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    price_max: Decimal | None = Field(default=None, ge=0, le=1_000_000)
    price_note: str | None = Field(default=None, max_length=200)
    is_available: bool | None = None
    locations: list[str] | None = None

    @field_validator("phone", "whatsapp_number")
    @classmethod
    def valid_phone(cls, v: str | None) -> str | None:
        return normalize_gh_phone(v)

    @field_validator("headline", "bio", "price_note")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        v = v.strip() if v else v
        return v or None

    @field_validator("locations")
    @classmethod
    def clean_locations(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned: list[str] = []
        for item in v:
            name = " ".join(item.split()).title()
            if not 2 <= len(name) <= 80:
                raise ValueError("Each service area must be between 2 and 80 characters")
            if name not in cleaned:
                cleaned.append(name)
        if len(cleaned) > 50:
            raise ValueError("You can list at most 50 service areas")
        return cleaned

    @model_validator(mode="after")
    def price_order(self):
        if self.price_min is not None and self.price_max is not None and self.price_max < self.price_min:
            raise ValueError("Maximum price cannot be lower than minimum price")
        return self


# ------------------------------------------------- service requests, reviews, notifications
from datetime import date  # noqa: E402

from models import RequestStatus  # noqa: E402


class PersonMini(BaseModel):
    id: int | None = None
    name: str
    profile_image: str | None = None


class RequestOut(BaseModel):
    id: int
    title: str
    status: RequestStatus
    category: str
    location: str
    preferred_date: date | None
    created_at: datetime
    updated_at: datetime
    other_party: PersonMini           # the artisan (for customers) or the customer (for artisans)
    photo_count: int
    has_review: bool


class RequestListOut(BaseModel):
    items: list[RequestOut]
    total: int
    page: int
    pages: int


class ReviewOut(BaseModel):
    id: int
    rating: int
    comment: str | None
    created_at: datetime
    reviewer_name: str                # shown as "Abena M." to protect privacy
    category: str | None = None
    artisan_name: str | None = None   # filled for "reviews I wrote"


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    pages: int
    avg_rating: Decimal
    review_count: int


class ContactInfo(BaseModel):
    name: str
    phone: str | None
    whatsapp_url: str | None


class RequestDetailOut(BaseModel):
    id: int
    title: str
    description: str
    status: RequestStatus
    status_note: str | None
    category: str
    location: str
    preferred_date: date | None
    created_at: datetime
    updated_at: datetime
    photos: list[str]
    viewer_role: str                  # "customer" | "artisan" | "admin"
    allowed_actions: list[str]        # statuses the viewer may move this request to
    artisan: PersonMini
    customer: PersonMini
    other_contact: ContactInfo | None # phone/WhatsApp of the other side (artisan: only after accepting)
    review: ReviewOut | None


class StatusUpdate(BaseModel):
    status: RequestStatus
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def clean_note(cls, v: str | None) -> str | None:
        v = v.strip() if v else v
        return v or None


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1500)

    @field_validator("comment")
    @classmethod
    def clean_comment(cls, v: str | None) -> str | None:
        v = v.strip() if v else v
        return v or None


class RequestSummary(BaseModel):
    pending: int
    active: int
    completed: int
    total: int


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    pages: int
