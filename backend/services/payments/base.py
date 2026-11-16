"""
The payment-provider contract.

Everything that talks to a payment company lives behind this interface, so the rest of the
app never depends on Paystack directly, and tests can use a simulated provider.
"""
from dataclasses import dataclass
from decimal import Decimal


class PaymentProviderError(Exception):
    """The provider could not be reached or refused the request."""


@dataclass
class CheckoutSession:
    authorization_url: str       # where we send the customer to pay
    provider_reference: str | None = None


@dataclass
class VerifiedCharge:
    status: str                  # "success" | "failed" | "pending"
    amount: Decimal              # in cedis
    currency: str
    reference: str
    channel: str | None = None


class PaymentProvider:
    name = "base"

    def initialize(self, *, reference: str, email: str, amount: Decimal, currency: str, callback_url: str,
                   channel: str | None, metadata: dict) -> CheckoutSession:
        raise NotImplementedError

    def verify(self, reference: str) -> VerifiedCharge:
        """Ask the provider directly what happened. This is the only thing we trust."""
        raise NotImplementedError

    def valid_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        raise NotImplementedError
