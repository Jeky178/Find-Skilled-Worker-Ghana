"""
BROWSER-TEST HARNESS ONLY. Runs the real app with a SIMULATED payment provider so the purchase screens can be
exercised without real money. Never imported by the application and not used in production.
   python tests/e2e_server.py
"""
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn  # noqa: E402

import routers.billing as billing  # noqa: E402
from config import get_settings  # noqa: E402
from services.payments.base import CheckoutSession, PaymentProvider, VerifiedCharge  # noqa: E402

settings = get_settings()
settings.PAYSTACK_SECRET_KEY = "sk_test_harness"
settings.VERIFICATION_FEE_GHS = Decimal("25")


class Simulated(PaymentProvider):
    name = "paystack"

    def __init__(self):
        self.orders: dict[str, VerifiedCharge] = {}

    def initialize(self, *, reference, email, amount, currency, callback_url, channel, metadata):
        product = metadata["product"]
        status = "pending" if product == "sponsored_30d" else "failed" if product == "sponsored_7d" else "success"
        self.orders[reference] = VerifiedCharge(status, amount, currency, reference, channel)
        return CheckoutSession(authorization_url=f"{callback_url}?reference={reference}")     # "the customer paid and came back"

    def verify(self, reference):
        return self.orders[reference]

    def valid_webhook_signature(self, raw_body, signature):
        return False


sim = Simulated()
billing.get_provider = lambda: sim
from main import app  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
