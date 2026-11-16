import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from config import get_settings
from database import Base, SessionLocal, engine
from routers import admin, artisan_me, artisans, auth, billing, categories, contact, notifications, reports, requests, reviews
from services.payments.fulfillment import expire_due_subscriptions

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fsw")

EXPIRY_CHECK_SECONDS = 900


def _run_expiry() -> int:
    with SessionLocal() as db:
        return expire_due_subscriptions(db)


async def _expiry_loop():
    """Every 15 minutes, end Premium plans whose time is up. Safe to run on several servers at once."""
    while True:
        try:
            await asyncio.to_thread(_run_expiry)
        except Exception:  # never let a hiccup kill the loop
            log.exception("subscription expiry check failed")
        await asyncio.sleep(EXPIRY_CHECK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT.lower() == "production":
        # Production never creates tables by itself: the schema is managed with Alembic migrations.
        if not inspect(engine).has_table("alembic_version"):
            raise RuntimeError("Database is not migrated. Run:  alembic upgrade head")
    else:
        Base.metadata.create_all(bind=engine)     # convenient for development
    task = asyncio.create_task(_expiry_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title=settings.APP_NAME, version="0.1.0",
    description="API for the Find a Skilled Worker Ghana marketplace.", lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None, redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.ENVIRONMENT.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Public uploads only (profile pictures, portfolio, request photos).
# Verification documents are stored elsewhere and served only to admins (Phase 2).
upload_dir = Path(settings.UPLOAD_DIR)
(upload_dir / "public").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir / "public"), name="uploads")

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(contact.router)
app.include_router(artisans.router)
app.include_router(artisan_me.router)
app.include_router(requests.router)
app.include_router(reviews.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(billing.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][-1]), "message": e["msg"].removeprefix("Value error, ")}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # Never leak stack traces to clients.
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


@app.get("/api/health/ready", tags=["System"])
def ready():
    """Readiness probe for hosting platforms: confirms the database answers."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "database unavailable"})
    return {"status": "ready"}


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "payments_enabled": settings.payments_enabled}
