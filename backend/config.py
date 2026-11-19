from decimal import Decimal
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Find a Skilled Worker Ghana"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./dev.db"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "uploads"
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    MAX_UPLOAD_MB: int = 5
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"
    FRONTEND_URL: str = "http://localhost:5173"      # where Paystack sends people back after paying
    ENABLE_API_DOCS: bool | None = None               # None = on in development, off in production

    # Prices in Ghana cedis. These are EXAMPLE values: set your own in .env.
    # A price of 0 means "not for sale" (verification at 0 = free verification).
    PREMIUM_PRICE_MONTHLY_GHS: Decimal = Decimal("50")
    PREMIUM_PRICE_YEARLY_GHS: Decimal = Decimal("500")
    VERIFICATION_FEE_GHS: Decimal = Decimal("0")
    SPONSORED_PRICE_7D_GHS: Decimal = Decimal("40")
    SPONSORED_PRICE_30D_GHS: Decimal = Decimal("120")

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_must_be_set(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be set in .env and be at least 32 characters long")
        return v

    @model_validator(mode="after")
    def production_must_be_safe(self):
        """Refuse to start in production with settings that are unsafe."""
        if self.ENVIRONMENT.lower() != "production":
            return self
        problems = []
        if self.DATABASE_URL.startswith("sqlite"):
            problems.append("DATABASE_URL must point to PostgreSQL, not SQLite")
        if "replace-with" in self.SECRET_KEY or "change" in self.SECRET_KEY.lower():
            problems.append("SECRET_KEY still looks like a placeholder")
        if not self.cors_origins_list or any(not o.startswith("https://") for o in self.cors_origins_list):
            problems.append("CORS_ORIGINS must list your https:// website address(es)")
        if not self.FRONTEND_URL.startswith("https://"):
            problems.append("FRONTEND_URL must be your https:// website address")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.ENABLE_API_DOCS if self.ENABLE_API_DOCS is not None else self.ENVIRONMENT.lower() != "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        """In development, accept the frontend on any localhost / 127.0.0.1 port (Vite may pick 5174, 5175...)."""
        if self.ENVIRONMENT.lower() == "production":
            return None
        return r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def payments_enabled(self) -> bool:
        return bool(self.PAYSTACK_SECRET_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()
