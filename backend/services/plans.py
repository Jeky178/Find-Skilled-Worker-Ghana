"""What each plan includes. Premium plans are architecture only until a payment provider is configured."""
from models import PlanType

PLAN_LIMITS = {
    PlanType.free: {"portfolio_images": 5},
    PlanType.premium: {"portfolio_images": 30},
}


def portfolio_limit(plan: PlanType) -> int:
    return PLAN_LIMITS[plan]["portfolio_images"]
