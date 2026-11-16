"""A stand-in for Paystack used ONLY by the tests (and the browser test harness). Never imported by the app."""
import hashlib
import hmac
from decimal import Decimal

from services.payments.base import CheckoutSession, PaymentProvider, PaymentProviderError, VerifiedCharge

SECRET = "sk_test_secret"


class FakeProvider(PaymentProvider):
    name = "paystack"

    def __init__(self, frontend="http://localhost:5174"):
        self.initialized: list[dict] = []
        self.results: dict[str, VerifiedCharge] = {}
        self.unreachable = False
        self.frontend = frontend

    def initialize(self, *, reference, email, amount, currency, callback_url, channel, metadata):
        if self.unreachable:
            raise PaymentProviderError("Could not reach the payment provider. Please try again.")
        self.initialized.append(dict(reference=reference, email=email, amount=amount, currency=currency, channel=channel, callback_url=callback_url))
        return CheckoutSession(authorization_url=f"https://checkout.test/pay/{reference}", provider_reference="ac_" + reference)

    def verify(self, reference):
        if self.unreachable:
            raise PaymentProviderError("down")
        return self.results.get(reference) or VerifiedCharge("pending", Decimal(0), "GHS", reference)

    def succeed(self, reference, amount, currency="GHS"):
        self.results[reference] = VerifiedCharge("success", Decimal(str(amount)), currency, reference, "mobile_money")

    def fail(self, reference, amount=0):
        self.results[reference] = VerifiedCharge("failed", Decimal(str(amount)), "GHS", reference)

    def valid_webhook_signature(self, raw_body, signature):
        return bool(signature) and hmac.compare_digest(sign(raw_body), signature)


def sign(raw: bytes) -> str:
    return hmac.new(SECRET.encode(), raw, hashlib.sha512).hexdigest()
