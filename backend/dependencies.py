from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth import decode_access_token
from database import get_db
from models import ArtisanProfile, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise _CREDENTIALS_ERROR
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _CREDENTIALS_ERROR
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR
    if user.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been suspended. Please contact support.")
    return user


def require_roles(*roles: UserRole):
    """Dependency factory: `Depends(require_roles(UserRole.admin))`."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user
    return checker


require_customer = require_roles(UserRole.customer)
require_artisan = require_roles(UserRole.artisan)
require_admin = require_roles(UserRole.admin)


def get_current_artisan_profile(user: User = Depends(require_artisan), db: Session = Depends(get_db)) -> ArtisanProfile:
    profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan profile not found")
    return profile
