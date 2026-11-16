from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from models import PaymentPurpose, PaymentStatus, PlanType, VerificationStatus


class ProductOut(BaseModel):
    code: str
    name: str
    description: str
    price_ghs: Decimal
    period_days: int
    purchasable: bool
    coming_soon: bool


class PlansOut(BaseModel):
    payments_enabled: bool
    currency: str
    products: list[ProductOut]


class BillingMeOut(BaseModel):
    plan: PlanType
    premium_until: datetime | None
    sponsored_until: datetime | None
    payments_enabled: bool
    verification_status: VerificationStatus
    verification_fee_ghs: Decimal
    verification_credit: bool          # a paid, unused verification fee is waiting


class CheckoutIn(BaseModel):
    product_code: str
    channel: Literal["mobile_money", "card"] | None = None


class CheckoutOut(BaseModel):
    reference: str
    authorization_url: str


class PaymentOut(BaseModel):
    reference: str
    product_code: str
    product_name: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime
    paid_at: datetime | None
    fulfilled: bool


class VerifyOut(BaseModel):
    reference: str
    status: Literal["completed", "pending", "failed"]
    product_code: str
    message: str


class AdminPaymentOut(BaseModel):
    id: int
    reference: str
    user_name: str
    user_email: str
    product_code: str
    purpose: PaymentPurpose
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str | None
    created_at: datetime
    paid_at: datetime | None
    fulfilled: bool


class AdminPaymentList(BaseModel):
    items: list[AdminPaymentOut]
    total: int
    page: int
    pages: int
    revenue_ghs: Decimal
    completed_count: int
