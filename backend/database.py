
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import get_settings

settings = get_settings()

database_url = settings.DATABASE_URL

# SQLite configuration
_connect_args = (
    {"check_same_thread": False}
    if database_url.startswith("sqlite")
    else {}
)

# PostgreSQL driver configuration
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

# Configure database engine
engine_options = {
    "connect_args": _connect_args,
    "pool_pre_ping": True,
}

# Production PostgreSQL connection pooling
if database_url.startswith("postgresql"):
    engine_options.update({
        "pool_size": 5,
        "max_overflow": 2,
        "pool_timeout": 30,
        "pool_recycle": 300,
    })

engine = create_engine(
    database_url,
    **engine_options
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
