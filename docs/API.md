# API reference

Generated from the code by `python scripts/export_api_docs.py`. The same information, with a **Try it out** button,
is at `/docs` while the backend runs in development (the page is switched off in production).

**Authentication.** Log in with `POST /api/auth/login`, then send the returned token on every protected call:
`Authorization: Bearer <token>`. Tokens last 60 minutes by default.

**Errors.** Failures return JSON with a `detail` message. Validation problems return `422` with an `errors` list of `{field, message}`.
Common codes: `401` not logged in, `403` wrong role or suspended, `404` not found (also used when you may not see something),
`409` conflict with the current state, `429` too many attempts, `503` payments not switched on.

**Who can call it** uses these labels: Public, Logged in, Customer, Artisan, Admin.

## System

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/health` | Public | Health |
| `GET` | `/api/health/ready` | Public | Readiness probe for hosting platforms: confirms the database answers. |

## Authentication

| Method | Path | Who | What it does |
|---|---|---|---|
| `POST` | `/api/auth/change-password` | Logged in | Change Password |
| `POST` | `/api/auth/login` | Public | Login |
| `GET` | `/api/auth/me` | Logged in | Me |
| `POST` | `/api/auth/register` | Public | Register |
| `POST` | `/api/auth/token` | Public | OAuth2 form login (used by the Swagger 'Authorize' button) |

## Categories

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/categories` | Public | List Categories |

## Artisan directory

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/artisans` | Public | List Artisans |
| `GET` | `/api/artisans/locations` | Public | Areas that have at least one visible artisan, for the location filter. |
| `GET` | `/api/artisans/{artisan_id}` | Public | Artisan Detail |
| `GET` | `/api/artisans/{artisan_id}/reviews` | Public | Artisan Reviews |

## Artisan profile (artisan only)

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/artisan/me` | Artisan | Get My Profile |
| `PATCH` | `/api/artisan/me` | Artisan | Update My Profile |
| `DELETE` | `/api/artisan/me/photo` | Artisan | Remove Profile Photo |
| `POST` | `/api/artisan/me/photo` | Artisan | Upload Profile Photo |
| `POST` | `/api/artisan/me/portfolio` | Artisan | Add Portfolio Image |
| `DELETE` | `/api/artisan/me/portfolio/{item_id}` | Artisan | Delete Portfolio Image |
| `GET` | `/api/artisan/me/verification` | Artisan | My Verification |
| `POST` | `/api/artisan/me/verification` | Artisan | ID documents are stored privately: never in the public uploads folder, and only admins can view them. |

## Billing and payments

| Method | Path | Who | What it does |
|---|---|---|---|
| `POST` | `/api/billing/checkout` | Artisan | Checkout |
| `GET` | `/api/billing/history` | Artisan | History |
| `GET` | `/api/billing/me` | Artisan | My Billing |
| `GET` | `/api/billing/plans` | Public | The public price list. `purchasable` is false for anything that cannot be bought right now. |
| `GET` | `/api/billing/verify/{reference}` | Artisan | Called when the customer returns from the payment page. Safe to call repeatedly. |
| `POST` | `/api/billing/webhook/paystack` | Paystack (signed) | Paystack calls this when a payment succeeds. We check the signature, then still ask Paystack's API to confirm before delivering anything, so a forged or replayed message cannot give anyone Premium. |

## Service requests

| Method | Path | Who | What it does |
|---|---|---|---|
| `POST` | `/api/requests` | Customer | Create Request |
| `GET` | `/api/requests/mine` | Logged in | My Requests |
| `GET` | `/api/requests/summary` | Logged in | Summary |
| `GET` | `/api/requests/{request_id}` | Logged in | Get Request |
| `POST` | `/api/requests/{request_id}/review` | Customer | Review Request |
| `PATCH` | `/api/requests/{request_id}/status` | Logged in | Update Status |

## Reviews

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/reviews/mine` | Logged in | Customers: reviews they wrote. Artisans: reviews they received. |

## Notifications

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/notifications` | Logged in | List Notifications |
| `POST` | `/api/notifications/read-all` | Logged in | Mark All Read |
| `GET` | `/api/notifications/unread-count` | Logged in | Unread Count |
| `POST` | `/api/notifications/{notification_id}/read` | Logged in | Mark Read |

## Reports

| Method | Path | Who | What it does |
|---|---|---|---|
| `POST` | `/api/reports` | Logged in | File Report |
| `GET` | `/api/reports/reasons` | Public | Reasons |

## Contact

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/contact` | Admin | List Messages |
| `POST` | `/api/contact` | Public | Send Message |
| `PATCH` | `/api/contact/{message_id}/read` | Admin | Mark Read |

## Administration

| Method | Path | Who | What it does |
|---|---|---|---|
| `GET` | `/api/admin/activity` | Admin | A merged, newest-first feed of what is happening on the platform. |
| `POST` | `/api/admin/artisans/{profile_id}/feature` | Admin | Set Featured |
| `POST` | `/api/admin/artisans/{profile_id}/plan` | Admin | Complimentary plan change by an admin. This records NO payment: paid plans arrive with the payment provider. |
| `GET` | `/api/admin/categories` | Admin | List Categories |
| `POST` | `/api/admin/categories` | Admin | Create Category |
| `PATCH` | `/api/admin/categories/{category_id}` | Admin | Update Category |
| `GET` | `/api/admin/payments` | Admin | Read-only. Admins cannot mark a payment as paid: only the payment provider's confirmation can do that. |
| `GET` | `/api/admin/reports` | Admin | List Reports |
| `PATCH` | `/api/admin/reports/{report_id}` | Admin | Update Report |
| `GET` | `/api/admin/requests` | Admin | Monitor Requests |
| `GET` | `/api/admin/stats` | Admin | Stats |
| `GET` | `/api/admin/users` | Admin | List Users |
| `POST` | `/api/admin/users/{user_id}/suspend` | Admin | Suspend User |
| `POST` | `/api/admin/users/{user_id}/unsuspend` | Admin | Unsuspend User |
| `GET` | `/api/admin/verifications` | Admin | List Verifications |
| `POST` | `/api/admin/verifications/{vid}/decision` | Admin | Decide Verification |
| `GET` | `/api/admin/verifications/{vid}/document` | Admin | Verification Document |
