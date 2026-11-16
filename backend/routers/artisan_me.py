"""An artisan managing their own profile, photo and portfolio."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from datetime import datetime, timezone

from database import get_db
from dependencies import require_artisan
from models import (
    ArtisanLocation, ArtisanPortfolio, ArtisanProfile, ServiceCategory, User, UserRole, Verification, VerificationStatus,
)
from schemas import MyProfileOut, PortfolioOut, ProfileUpdate
from schemas_admin import ID_TYPES, MyVerificationOut
from config import get_settings
from services.notifications import notify
from services.payments.fulfillment import verification_credit
from services.artisan_views import to_my_profile
from services.plans import portfolio_limit
from services.uploads import delete_image, save_image

router = APIRouter(prefix="/api/artisan/me", tags=["Artisan profile (artisan only)"])


def _own_profile(user: User = Depends(require_artisan), db: Session = Depends(get_db)) -> ArtisanProfile:
    p = (
        db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id)
        .options(selectinload(ArtisanProfile.locations), selectinload(ArtisanProfile.portfolio))
        .first()
    )
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan profile not found")
    return p


@router.get("", response_model=MyProfileOut)
def get_my_profile(p: ArtisanProfile = Depends(_own_profile)):
    return to_my_profile(p)


@router.patch("", response_model=MyProfileOut)
def update_my_profile(data: ProfileUpdate, p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)

    if "category_id" in changes and changes["category_id"] is not None:
        cat = db.get(ServiceCategory, changes["category_id"])
        if cat is None or not cat.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Selected occupation does not exist")
        p.category_id = cat.id

    new_min = changes.get("price_min", p.price_min)
    new_max = changes.get("price_max", p.price_max)
    if new_min is not None and new_max is not None and new_max < new_min:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Maximum price cannot be lower than minimum price")

    for field in ("headline", "bio", "years_experience", "phone", "whatsapp_number",
                  "price_min", "price_max", "price_note", "is_available"):
        if field in changes and (changes[field] is not None or field in ("headline", "bio", "phone", "whatsapp_number", "price_min", "price_max", "price_note")):
            setattr(p, field, changes[field])

    if changes.get("locations") is not None:
        wanted = changes["locations"]
        p.locations[:] = [l for l in p.locations if l.location in wanted]
        have = {l.location for l in p.locations}
        p.locations.extend(ArtisanLocation(location=name) for name in wanted if name not in have)

    db.commit()
    db.refresh(p)
    return to_my_profile(p)


@router.post("/photo", response_model=MyProfileOut)
def upload_profile_photo(file: UploadFile = File(...), p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db)):
    new_path = save_image(file, "profiles")
    old = p.profile_image
    p.profile_image = new_path
    db.commit()
    delete_image(old)
    db.refresh(p)
    return to_my_profile(p)


@router.delete("/photo", response_model=MyProfileOut)
def remove_profile_photo(p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db)):
    old, p.profile_image = p.profile_image, None
    db.commit()
    delete_image(old)
    db.refresh(p)
    return to_my_profile(p)


@router.post("/portfolio", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def add_portfolio_image(
    file: UploadFile = File(...), caption: str | None = Form(None, max_length=200),
    p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db),
):
    limit = portfolio_limit(p.plan)
    if len(p.portfolio) >= limit:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Your {p.plan.value} plan allows up to {limit} portfolio photos. Remove one to add another"
            + (", or upgrade to Premium for more." if p.plan.value == "free" else "."),
        )
    path = save_image(file, "portfolio")
    item = ArtisanPortfolio(artisan_id=p.id, image_path=path, caption=(caption or "").strip() or None)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PortfolioOut(id=item.id, image_url=item.image_path, caption=item.caption)


@router.delete("/portfolio/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_image(item_id: int, p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db)):
    item = db.query(ArtisanPortfolio).filter(ArtisanPortfolio.id == item_id, ArtisanPortfolio.artisan_id == p.id).first()
    if item is None:  # also covers trying to delete another artisan's photo
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    path = item.image_path
    db.delete(item)
    db.commit()
    delete_image(path)


# --------------------------------------------------------------- verification
@router.get("/verification", response_model=MyVerificationOut)
def my_verification(p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db)):
    latest = db.query(Verification).filter(Verification.artisan_id == p.id).order_by(Verification.id.desc()).first()
    return MyVerificationOut(status=p.verification_status, id_type=latest.id_type if latest else None,
                             admin_note=latest.admin_note if latest and latest.status == VerificationStatus.rejected else None,
                             submitted_at=latest.created_at if latest else None)


@router.post("/verification", response_model=MyVerificationOut, status_code=status.HTTP_201_CREATED)
def apply_for_verification(
    id_type: str = Form(...), document: UploadFile = File(...), certificate: UploadFile | None = File(None),
    p: ArtisanProfile = Depends(_own_profile), db: Session = Depends(get_db),
):
    """ID documents are stored privately: never in the public uploads folder, and only admins can view them."""
    if id_type not in ID_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a valid ID type")
    if p.verification_status == VerificationStatus.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "You are already verified")
    if p.verification_status == VerificationStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your application is already being reviewed")

    settings = get_settings()
    credit = None
    if settings.payments_enabled and settings.VERIFICATION_FEE_GHS > 0:      # paid verification, only when payments are really on
        credit = verification_credit(db, p.user_id)
        if credit is None:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED,
                                f"Verification costs GH₵{settings.VERIFICATION_FEE_GHS:,.2f}. Pay the fee first, then submit your documents.")

    saved: list[str] = []
    try:
        saved.append(save_image(document, "verification", private=True, max_side=2200))
        if certificate is not None and certificate.filename:
            saved.append(save_image(certificate, "verification", private=True, max_side=2200))
    except HTTPException:
        for key in saved:
            delete_image(key)
        raise

    v = Verification(artisan_id=p.id, id_type=id_type, document_path=saved[0], trade_certificate_path=saved[1] if len(saved) > 1 else None)
    db.add(v)
    db.flush()
    if credit is not None:
        credit.consumed_at, credit.target_id = datetime.now(timezone.utc), v.id
    p.verification_status = VerificationStatus.pending
    for (admin_id,) in db.query(User.id).filter(User.role == UserRole.admin, User.is_active.is_(True)).all():
        notify(db, admin_id, "New verification application", f"{p.user.full_name} applied to be verified.", "/admin/verifications")
    db.commit()
    return MyVerificationOut(status=p.verification_status, id_type=id_type, submitted_at=v.created_at)
