# Find a Skilled Worker Ghana

A marketplace that connects people in Ghana with trusted skilled workers: plumbers, electricians, carpenters, painters, mechanics, AC and refrigeration technicians, tilers, welders, POP ceiling installers, cleaners and appliance repairers. It launches in Accra (Madina, Adenta, Dome, East Legon, Haatso, Achimota, Kasoa) and is built to grow nationwide.

**Stack:** Python, FastAPI, SQLAlchemy, PostgreSQL, Pydantic v2, JWT · React, Vite, Tailwind CSS, Axios, React Router · Paystack (cards and Mobile Money).

## What it does

| Who | They can |
|---|---|
| **Customers** | Register and log in · search artisans by trade, area, availability and verification · read profiles, prices, portfolios and reviews · request a service with a description and up to 5 photos · contact artisans on WhatsApp · track a request from sent to completed · rate finished jobs · report problems · get notifications |
| **Artisans** | Register with a trade and area · build a profile (photo, bio, prices, areas, portfolio photos, availability) · receive requests and accept, decline, start or complete them · see customer contact details after accepting · read reviews · apply for the Verified badge · buy Premium, sponsored listings and verification (when payments are on) |
| **Administrators** | See every customer, artisan and request · approve or reject verification applications (private ID documents) · suspend and reinstate accounts · feature artisans and grant plans · manage service categories · handle reports and contact messages · view confirmed payments and revenue · review platform activity and an audit trail of every admin action |

## Revenue model (built in, off until you switch payments on)

- **Free plan:** basic profile, 5 portfolio photos, standard listing.
- **Premium:** priority in search, Premium badge, 30 portfolio photos. Monthly or yearly.
- **Sponsored listings:** featured at the top of results and on the homepage for 7 or 30 days.
- **Paid verification:** an optional fee per verification review (free by default).
- **Business plans:** shown as "coming soon" (not built).

No payment is ever marked as received unless Paystack confirms it. With no Paystack key configured, nothing can be bought. See [docs/PAYMENTS.md](docs/PAYMENTS.md).

## Project structure

```
find_skilled_worker/
├── backend/                 FastAPI application
│   ├── main.py              app, middleware, startup
│   ├── config.py            settings from .env (with production safety checks)
│   ├── database.py  models.py  schemas.py  schemas_admin.py  schemas_billing.py
│   ├── auth.py  dependencies.py       passwords, JWT, role checks
│   ├── routers/             auth, categories, contact, artisans, artisan_me, requests, reviews,
│   │                        notifications, reports, billing, admin
│   ├── services/            uploads, notifications, audit, pricing, request rules, payments/ (Paystack)
│   ├── migrations/          Alembic database migrations
│   ├── tests/               automated tests
│   ├── seed.py  create_admin.py  jobs.py   command-line tools
│   └── uploads/             public/ (photos) and private/ (ID documents)
├── frontend/                React + Vite + Tailwind website
│   └── src/  pages/  components/  layouts/  services/  context/  hooks/
├── docs/                    API.md, DEPLOYMENT.md, PAYMENTS.md, USER_GUIDE.md
├── scripts/export_api_docs.py
├── docker-compose.yml  .env.production.example
└── README.md
```

## Quick start (development)

You need **Python 3.12+**, **Node.js 20+** (LTS) and **PostgreSQL 14+**.

**1. Create the database** (pgAdmin Query Tool or `psql`; run each statement on its own):

```sql
CREATE USER skilled_user WITH PASSWORD 'choose-a-password';
CREATE DATABASE find_skilled_worker OWNER skilled_user;
```

**2. Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
python -m pip install -r requirements.txt
copy .env.example .env           # Mac/Linux: cp .env.example .env
```

Edit `.env`: set `DATABASE_URL` (your password) and `SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).

```bash
python seed.py                   # creates the 12 service categories (add --demo for sample artisans)
python create_admin.py           # creates your administrator account
uvicorn main:app --reload        # API on http://localhost:8000, docs at /docs
```

**3. Frontend** (second terminal)

```bash
cd frontend
copy .env.example .env
npm install
npm run dev                      # website on http://localhost:5173
```

Open http://localhost:5173. Log in with the admin you created. Remove sample data any time with `python seed.py --remove-demo`.

> **Windows PowerShell says scripts are disabled?** Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once, or use Command Prompt.

## Configuration

All settings live in `backend/.env` (see `backend/.env.example`) and `frontend/.env`.

| Setting | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Signs login tokens. At least 32 random characters. Keep it secret |
| `ENVIRONMENT` | `development` or `production`. Production enables strict startup checks |
| `CORS_ORIGINS`, `FRONTEND_URL` | Your website address(es). Must be `https://` in production |
| `PAYSTACK_SECRET_KEY` | Blank = payments off. `sk_test_...` to test, `sk_live_...` to go live |
| `PREMIUM_PRICE_*`, `SPONSORED_PRICE_*`, `VERIFICATION_FEE_GHS` | Prices in GH₵ (0 = not for sale) |
| `MAX_UPLOAD_MB`, `UPLOAD_DIR` | Image size limit and where files are stored |
| `VITE_API_URL` (frontend) | Backend address. Empty = same address as the website |

## Database and migrations

- **Development:** tables are created automatically when the API starts, so you need no extra step.
- **Production:** the API refuses to start until the database is migrated. Run `alembic upgrade head` (the Docker setup does this for you).
- **Already have a development database?** Run `alembic stamp head` once so Alembic knows it is up to date.
- **After changing a model:** `alembic revision --autogenerate -m "describe the change"`, review the file, then `alembic upgrade head`.

## Running the tests

```bash
cd backend
python -m pytest -q                                   # runs on a temporary SQLite file
```

To run them on your real kind of database, point the tests at an empty PostgreSQL database (they erase its tables, so never use your real one):

```bash
set DATABASE_URL=postgresql+psycopg2://skilled_user:password@localhost:5432/fsw_test    # Mac/Linux: export
python -m pytest -q
```

75 tests cover authentication, roles, uploads and image validation, the artisan directory, service requests and every status rule, reviews and ratings, notifications, verification, reports, categories, featured listings, payments (with a simulated provider, plus the real Paystack adapter against recorded responses), subscription expiry, and production safety checks. They pass on both SQLite and PostgreSQL.

## API documentation

[docs/API.md](docs/API.md) lists all 59 endpoints (regenerate with `python scripts/export_api_docs.py`). While the backend runs in development, interactive docs are at http://localhost:8000/docs.

## Security

Passwords are hashed with bcrypt and never stored in plain text. Logins use signed JWT tokens with role checks on every protected route. Login attempts are rate-limited, and suspended accounts are blocked immediately. All input is validated. Uploaded images are checked by content (not file name), re-encoded and stripped of metadata. ID documents are stored outside the public folder and only admins can open them. Payment confirmations are checked directly with Paystack, with amount and currency verified, and webhooks need a valid signature. Production refuses to start with unsafe settings (SQLite, placeholder secrets, non-HTTPS addresses), hides the API docs and sends security headers.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): a Docker Compose setup with automatic HTTPS, backups, updates and a go-live checklist.

## Known limitations

- Notifications are in-app only (no email or SMS yet), and there is no email verification or password reset.
- The login rate limiter lives in server memory. With several servers, move it to Redis.
- Uploaded files are stored on the server's disk. Use object storage (S3-compatible) if you scale out.
- Payments cover artisan plans only. Customer-to-artisan payments for the actual work happen outside the platform.
- No automatic refunds or recurring card billing: plans are bought for a period and renewed by the artisan.
- Business plans and chat inside the app are not built.
