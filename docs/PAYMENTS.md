# Payments guide

The platform charges **artisans** for optional extras: Premium plans, sponsored listings and (if you want) a verification fee. Customers pay artisans for the actual work directly, outside the platform.

Payments use **Paystack**, which accepts cards and **Mobile Money** (MTN, Telecel, AirtelTigo) in Ghana. The customer pays on Paystack's own hosted page, so card and wallet details never touch your server.

> **Honest note:** this was tested with a simulated payment provider and recorded Paystack-style responses, **not against the live Paystack service** (it cannot be reached from where this was built). Always test with your Paystack **test keys** and a few small real payments before announcing paid plans.

## The rule everything follows

**Nothing is delivered until Paystack's server confirms the money.** Not the customer's browser, not a webhook alone, not an admin.

1. The artisan chooses a product. The server records a **pending** payment and asks Paystack for a payment page.
2. The artisan pays on Paystack and is sent back to `/billing/callback`.
3. The server asks Paystack's API what really happened (`transaction/verify`).
4. Only if Paystack says `success` **and** the reference, amount and currency exactly match the order, the server marks the payment paid and delivers the product (Premium, sponsorship or verification credit).
5. Paystack's webhook (`/api/billing/webhook/paystack`) does the same check from Paystack's side, in case the customer closed the browser. It needs a valid HMAC-SHA512 signature, and it still verifies with Paystack before delivering anything.

Delivery happens **once**, even if the callback and the webhook arrive together or are repeated. If Paystack reports a different amount or currency, the order is marked failed, nothing is delivered, and an error is logged for you to investigate.

**With no `PAYSTACK_SECRET_KEY` set, online payments are off:** checkout returns "not switched on", buy buttons are disabled and explained, and nothing is ever recorded as paid. Administrators cannot mark a payment as paid either.

## Products and prices

Set in `backend/.env` (or the root `.env` for Docker), in Ghana cedis:

| Setting | Product |
|---|---|
| `PREMIUM_PRICE_MONTHLY_GHS` | Premium, 30 days |
| `PREMIUM_PRICE_YEARLY_GHS` | Premium, 365 days |
| `SPONSORED_PRICE_7D_GHS`, `SPONSORED_PRICE_30D_GHS` | Featured listing for 7 or 30 days |
| `VERIFICATION_FEE_GHS` | Fee per verification application. **0 = free** |

The shipped numbers are examples. A price of 0 removes the product. Renewing Premium before it ends adds time on top of the current period. Sponsored time stacks the same way, and never shortens an admin's permanent feature. Premium ends automatically (checked every 15 minutes) and the artisan returns to the Free plan, keeping existing photos but unable to add more than 5.

The verification fee covers **one application**. If an application is rejected, applying again needs a new fee. If you prefer to let rejected artisans re-apply free, that is a small change.

## Testing with Paystack test keys

1. Create a Paystack account and, in the dashboard, copy your **test secret key** (`sk_test_...`).
2. Put it in `PAYSTACK_SECRET_KEY`, restart the backend.
3. Log in as an artisan, open **Dashboard → Plans and billing**. The "not switched on" banner disappears and the buy buttons work.
4. Buy Premium. You are taken to Paystack's test checkout. Use the test card and test Mobile Money details from Paystack's documentation (**paystack.com/docs → Testing**).
5. After paying you return to the site and see "Payment confirmed". Check that the artisan now has the Premium badge, and that **Admin → Payments** shows it and the confirmed revenue.
6. **Webhook:** Paystack must reach your server over the internet. In the Paystack dashboard (Settings → API Keys & Webhooks) set the webhook URL to `https://your-domain/api/billing/webhook/paystack`. For local testing use a tunnel tool such as ngrok. The callback page works without the webhook, so you can test that first.
7. Also test: closing the browser before returning (the webhook should still deliver), a failed payment, and an abandoned one (it stays "Unconfirmed").

## Going live

1. Complete Paystack's business verification so you can accept live payments.
2. Replace the key with your **live** secret key (`sk_live_...`), set the live webhook URL, and redeploy.
3. Make one small real purchase yourself, confirm the delivery, and check the money arrives in your Paystack balance.
4. Check **Admin → Payments** regularly for rows marked "NOT DELIVERED" (paid but not delivered) or old "Unconfirmed" ones.

## What it does not do (yet)

- **Refunds:** do them in the Paystack dashboard. The app does not undo a delivered plan automatically.
- **Receipts and invoices:** Paystack emails its own receipt. The app lists payment history only.
- **Auto-renewal:** plans are bought for a period and renewed by the artisan. There is no recurring card charge.
- **Direct Mobile Money integrations:** Mobile Money works through Paystack's checkout. Direct MTN MoMo API integration is not built.
- **Paying artisans for jobs, escrow, or commission on jobs:** not built.
- **Business plans:** shown as "coming soon".

## Where the code is

`backend/services/payments/` holds the provider interface (`base.py`), Paystack (`paystack.py`) and delivery logic (`fulfillment.py`). `backend/routers/billing.py` has the endpoints. To add another provider later, implement the same interface and return it from `get_provider()`.
