from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import get_db
from dependencies import get_current_user
from models import ArtisanLocation, ArtisanProfile, ServiceCategory, User, UserRole
from schemas import ChangePasswordRequest, LoginRequest, MeOut, RegisterRequest, TokenOut
from services import rate_limit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _login(db: Session, email: str, password: str, request: Request) -> User:
    key = f"{request.client.host if request.client else 'unknown'}:{email}"
    if rate_limit.is_blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in 15 minutes.")
    user = db.query(User).filter(User.email == email).first()
    if not verify_password(password, user.password_hash if user else None):
        rate_limit.record_failure(key)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is deactivated")
    if user.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been suspended. Please contact support.")
    rate_limit.reset(key)
    return user


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    category = None
    if data.role == UserRole.artisan:
        category = db.get(ServiceCategory, data.category_id)
        if category is None or not category.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Selected occupation does not exist")

    user = User(
        full_name=data.full_name, email=data.email, phone=data.phone,
        password_hash=hash_password(data.password), role=data.role,
    )
    db.add(user)
    db.flush()

    if category is not None:
        profile = ArtisanProfile(user_id=user.id, category_id=category.id, phone=data.phone, whatsapp_number=data.phone)
        if data.location:
            profile.locations.append(ArtisanLocation(location=data.location.strip().title()))
        db.add(profile)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _login(db, data.email, data.password, request)
    return TokenOut(access_token=create_access_token(user.id, user.role.value), user=user)


@router.post("/token", include_in_schema=True, summary="OAuth2 form login (used by the Swagger 'Authorize' button)")
def token(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _login(db, form.username.lower(), form.password, request)
    return {"access_token": create_access_token(user.id, user.role.value), "token_type": "bearer"}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePasswordRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
