"""The product catalogue. Prices come from settings (.env), so you can change them without touching code."""
from dataclasses import dataclass
from decimal import Decimal

from config import Settings, get_settings
from models import PaymentPurpose


@dataclass(frozen=True)
class Product:
    code: str
    name: str
    description: str
    purpose: PaymentPurpose
    price: Decimal            # Ghana cedis
    period_days: int
    available: bool = True    # False = shown as "coming soon", cannot be bought

    @property
    def purchasable(self) -> bool:
        return self.available and self.price > 0


def catalog(settings: Settings | None = None) -> list[Product]:
    s = settings or get_settings()
    return [
        Product("premium_monthly", "Premium, 1 month", "Featured-style priority in search, a Premium badge, 30 portfolio photos.",
                PaymentPurpose.subscription, s.PREMIUM_PRICE_MONTHLY_GHS, 30),
        Product("premium_yearly", "Premium, 12 months", "Everything in Premium for a full year at a lower monthly cost.",
                PaymentPurpose.subscription, s.PREMIUM_PRICE_YEARLY_GHS, 365),
        Product("verification", "Verification fee", "One review of your ID by our team for the Verified badge.",
                PaymentPurpose.verification, s.VERIFICATION_FEE_GHS, 0),
        Product("sponsored_7d", "Sponsored listing, 7 days", "Your profile is featured at the top of results and on the homepage for 7 days.",
                PaymentPurpose.sponsored_listing, s.SPONSORED_PRICE_7D_GHS, 7),
        Product("sponsored_30d", "Sponsored listing, 30 days", "Your profile is featured at the top of results and on the homepage for 30 days.",
                PaymentPurpose.sponsored_listing, s.SPONSORED_PRICE_30D_GHS, 30),
        Product("business_plan", "Business plan", "Team accounts for companies with several workers.",
                PaymentPurpose.business_subscription, Decimal("0"), 30, available=False),
    ]


def get_product(code: str) -> Product | None:
    return next((p for p in catalog() if p.code == code), None)
