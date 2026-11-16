import os

# Must be set before the app is imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")   # pass a PostgreSQL URL to run the suite on PostgreSQL
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-1234567890"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
import tempfile
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="fsw_uploads_")

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
