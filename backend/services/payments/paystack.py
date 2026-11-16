"""
Paystack (cards and Mobile Money: MTN MoMo, Telecel Cash, AirtelTigo Money) for Ghana.

Flow:  initialize -> customer pays on Paystack's hosted page -> we VERIFY with Paystack's API
(never trusting the browser or the webhook body alone) -> fulfil.
Docs: https://paystack.com/docs/api/transaction/
"""
import hashlib
import hmac
from decimal import Decimal

import httpx

from config import get_settings
from services.payments.base import CheckoutSession, PaymentProvider, PaymentProviderError, VerifiedCharge

_CHANNELS = {"mobile_money": ["mobile_money"], "card": ["card"]}


class PaystackProvider(PaymentProvider):
    name = "paystack"

    def __init__(self, secret_key: str, base_url: str):
        self.secret = secret_key
        self.base = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kw) -> dict:
        try:
            r = httpx.request(method, f"{self.base}{path}", headers={"Authorization": f"Bearer {self.secret}"}, timeout=15, **kw)
            body = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("Could not reach the payment provider. Please try again.") from exc
        if r.status_code >= 400 or not body.get("status"):
            raise PaymentProviderError(body.get("message") or "The payment provider rejected the request.")
        return body["data"]

    def initialize(self, *, reference, email, amount, currency, callback_url, channel, metadata) -> CheckoutSession:
        payload = {
            "email": email, "amount": int((amount * 100).to_integral_value()),   # pesewas
            "currency": currency, "reference": reference, "callback_url": callback_url, "metadata": metadata,
        }
        if channel in _CHANNELS:
            payload["channels"] = _CHANNELS[channel]
        data = self._request("POST", "/transaction/initialize", json=payload)
        return CheckoutSession(authorization_url=data["authorization_url"], provider_reference=data.get("access_code"))

    def verify(self, reference: str) -> VerifiedCharge:
        data = self._request("GET", f"/transaction/verify/{reference}")
        raw = data.get("status", "")
        status = "success" if raw == "success" else "failed" if raw in ("failed", "reversed") else "pending"
        return VerifiedCharge(status=status, amount=Decimal(data.get("amount", 0)) / 100, currency=data.get("currency", ""),
                              reference=data.get("reference", reference), channel=data.get("channel"))

    def valid_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            return False
        expected = hmac.new(self.secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature.lower())


def get_provider() -> PaymentProvider | None:
    """None when no provider is configured. Callers must then refuse to take payments."""
    s = get_settings()
    return PaystackProvider(s.PAYSTACK_SECRET_KEY, s.PAYSTACK_BASE_URL) if s.payments_enabled else None
