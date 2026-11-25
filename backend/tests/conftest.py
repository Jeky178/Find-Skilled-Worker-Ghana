import os
import tempfile

# Test environment settings must be set before importing the app.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-1234567890"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="fsw_uploads_")

# Disable external services during tests.
os.environ["ENVIRONMENT"] = "test"

os.environ["CLOUDINARY_CLOUD_NAME"] = ""
os.environ["CLOUDINARY_API_KEY"] = ""
os.environ["CLOUDINARY_API_SECRET"] = ""

os.environ["PAYSTACK_SECRET_KEY"] = ""
os.environ["VERIFICATION_FEE_GHS"] = "0"

import pytest
from fastapi.testclient import TestClient

from database import Base, SessionLocal, engine
from main import app
from models import ServiceCategory
from services import rate_limit


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    rate_limit._attempts.clear()
    with SessionLocal() as db:
        db.add(ServiceCategory(name="Plumber", slug="plumber", icon="wrench"))
        db.add(ServiceCategory(name="Electrician", slug="electrician", icon="zap"))
        db.commit()
    with TestClient(app) as c:
        yield c
