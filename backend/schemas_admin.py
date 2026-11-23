from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from models import PlanType, ReportStatus, RequestStatus, UserRole, VerificationStatus

REPORT_REASONS = [
    "Fake or misleading profile", "Unprofessional behaviour", "Poor or unfinished work",
    "Asked for payment outside the platform", "Harassment or abuse", "Scam or fraud", "Other",
]
ID_TYPES = ["Ghana Card", "Driver's Licence", "Passport", "Voter ID"]


def _strip(v: str | None) -> str | None:
    v = v.strip() if v else v
    return v or None


class AdminUserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_suspended: bool
    suspended_reason: str | None
    created_at: datetime
    artisan_id: int | None = None
    category: str | None = None
    verification_status: VerificationStatus | None = None
    plan: PlanType | None = None
    is_featured: bool | None = None
    featured_until: datetime | None = None


class AdminUserList(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    pages: int


class SuspendIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean(cls, v: str) -> str:
        return v.strip()


class FeatureIn(BaseModel):
    featured: bool
    until: date | None = None      # last day the listing is featured; empty = until switched off


class PlanIn(BaseModel):
    plan: PlanType


class VerificationAdminOut(BaseModel):
    id: int
    status: VerificationStatus
    id_type: str
    created_at: datetime
    reviewed_at: datetime | None
    admin_note: str | None
    artisan_id: int
    artisan_name: str
    artisan_email: EmailStr
    category: str
    has_certificate: bool


class VerificationListOut(BaseModel):
    items: list[VerificationAdminOut]
    total: int
    page: int
    pages: int


class MyVerificationOut(BaseModel):
    status: VerificationStatus
    id_type: str | None = None
    admin_note: str | None = None
    submitted_at: datetime | None = None


class DecisionIn(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def clean(cls, v: str | None) -> str | None:
        return _strip(v)


class CategoryAdminOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    icon: str | None
    is_active: bool
    artisan_count: int


class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("description", "icon")
    @classmethod
    def clean(cls, v: str | None) -> str | None:
        return _strip(v)


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    icon: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v else v


class AdminRequestOut(BaseModel):
    id: int
    title: str
    status: RequestStatus
    category: str
    location: str
    customer_name: str
    artisan_name: str
    created_at: datetime
    updated_at: datetime


class AdminRequestList(BaseModel):
    items: list[AdminRequestOut]
    total: int
    page: int
    pages: int


class ReportIn(BaseModel):
    artisan_id: int | None = None
    request_id: int | None = None
    reason: str
    details: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def valid_reason(cls, v: str) -> str:
        if v not in REPORT_REASONS:
            raise ValueError("Please choose a reason from the list")
        return v

    @field_validator("details")
    @classmethod
    def clean(cls, v: str | None) -> str | None:
        return _strip(v)


class ReportAdminOut(BaseModel):
    id: int
    status: ReportStatus
    reason: str
    details: str | None
    admin_note: str | None
    created_at: datetime
    reporter_name: str
    reported_user_id: int
    reported_name: str
    reported_role: UserRole
    reported_suspended: bool
    request_id: int | None
    request_title: str | None


class ReportListOut(BaseModel):
    items: list[ReportAdminOut]
    total: int
    page: int
    pages: int


class ReportUpdate(BaseModel):
    status: ReportStatus
    admin_note: str | None = Field(default=None, max_length=500)

    @field_validator("admin_note")
    @classmethod
    def clean(cls, v: str | None) -> str | None:
        return _strip(v)


class ActivityItem(BaseModel):
    kind: str
    text: str
    at: datetime
    link: str | None = None


class AdminStats(BaseModel):
    customers: int
    artisans: int
    admins: int
    suspended_users: int
    new_users_7d: int
    verification_unverified: int
    verification_pending: int
    verification_approved: int
    verification_rejected: int
    featured_artisans: int
    premium_artisans: int
    requests_total: int
    requests_pending: int
    requests_active: int
    requests_completed: int
    requests_closed: int
    reviews_total: int
    open_reports: int
    unread_messages: int
    revenue_ghs: Decimal = Decimal(0)
    payments_pending: int = 0
    active_premium: int = 0
