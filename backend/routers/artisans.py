"""Public artisan directory: search, filters, sorting and profile pages."""
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, exists, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models import ArtisanLocation, ArtisanProfile, PlanType, ServiceCategory, User, VerificationStatus
from models import Review
from schemas import ArtisanDetailOut, ArtisanListOut, LocationCount, ReviewListOut
from services.request_views import to_review_out
from services.artisan_views import to_card, to_detail

router = APIRouter(prefix="/api/artisans", tags=["Artisan directory"])

SortKey = Literal["recommended", "rating", "experience", "newest", "price_low"]


# A listing counts as featured only while its (optional) expiry date has not passed.
FEATURED = and_(ArtisanProfile.is_featured.is_(True), or_(ArtisanProfile.featured_until.is_(None), ArtisanProfile.featured_until > func.now()))


def _visible():
    """Suspended or deactivated accounts never appear publicly."""
    return (User.is_active.is_(True), User.is_suspended.is_(False))


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=ArtisanListOut)
def list_artisans(
    q: str | None = Query(None, max_length=100, description="Search name, headline, bio or trade"),
    category: str | None = Query(None, description="Category slug, e.g. plumber"),
    location: str | None = Query(None, max_length=80),
    available_only: bool = False,
    verified_only: bool = False,
    featured_only: bool = False,
    min_rating: float | None = Query(None, ge=0, le=5),
    sort: SortKey = "recommended",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ArtisanProfile)
        .join(User, ArtisanProfile.user_id == User.id)
        .join(ServiceCategory, ArtisanProfile.category_id == ServiceCategory.id)
        .filter(*_visible(), ServiceCategory.is_active.is_(True))
    )
    if category:
        query = query.filter(ServiceCategory.slug == category.lower())
    if location:
        query = query.filter(exists().where(
            ArtisanLocation.artisan_id == ArtisanProfile.id,
            func.lower(ArtisanLocation.location) == location.strip().lower(),
        ))
    if q and q.strip():
        like = f"%{_escape_like(q.strip())}%"
        query = query.filter(or_(
            User.full_name.ilike(like, escape="\\"),
            ArtisanProfile.headline.ilike(like, escape="\\"),
            ArtisanProfile.bio.ilike(like, escape="\\"),
            ServiceCategory.name.ilike(like, escape="\\"),
        ))
    if available_only:
        query = query.filter(ArtisanProfile.is_available.is_(True))
    if verified_only:
        query = query.filter(ArtisanProfile.verification_status == VerificationStatus.approved)
    if featured_only:
        query = query.filter(FEATURED)
    if min_rating is not None:
        query = query.filter(ArtisanProfile.avg_rating >= min_rating)

    total = query.with_entities(func.count(ArtisanProfile.id)).scalar() or 0

    if sort == "rating":
        order = [ArtisanProfile.avg_rating.desc(), ArtisanProfile.review_count.desc(), ArtisanProfile.id.desc()]
    elif sort == "experience":
        order = [ArtisanProfile.years_experience.desc(), ArtisanProfile.id.desc()]
    elif sort == "newest":
        order = [ArtisanProfile.id.desc()]
    elif sort == "price_low":
        order = [ArtisanProfile.price_min.is_(None), ArtisanProfile.price_min.asc(), ArtisanProfile.id.desc()]
    else:  # recommended: featured and premium listings get priority visibility, then quality signals
        order = [
            case((FEATURED, 1), else_=0).desc(),
            case((ArtisanProfile.plan == PlanType.premium, 1), else_=0).desc(),
            case((ArtisanProfile.verification_status == VerificationStatus.approved, 1), else_=0).desc(),
            ArtisanProfile.avg_rating.desc(),
            ArtisanProfile.review_count.desc(),
            ArtisanProfile.id.desc(),
        ]

    rows = (
        query.options(joinedload(ArtisanProfile.user), joinedload(ArtisanProfile.category), selectinload(ArtisanProfile.locations))
        .order_by(*order).offset((page - 1) * page_size).limit(page_size).all()
    )
    return ArtisanListOut(items=[to_card(p) for p in rows], total=total, page=page, pages=max(1, math.ceil(total / page_size)))


@router.get("/locations", response_model=list[LocationCount])
def list_locations(db: Session = Depends(get_db)):
    """Areas that have at least one visible artisan, for the location filter."""
    rows = (
        db.query(ArtisanLocation.location, func.count(ArtisanLocation.id))
        .join(ArtisanProfile, ArtisanLocation.artisan_id == ArtisanProfile.id)
        .join(User, ArtisanProfile.user_id == User.id)
        .filter(*_visible())
        .group_by(ArtisanLocation.location)
        .order_by(ArtisanLocation.location)
        .all()
    )
    return [LocationCount(location=loc, count=n) for loc, n in rows]


@router.get("/{artisan_id}", response_model=ArtisanDetailOut)
def artisan_detail(artisan_id: int, db: Session = Depends(get_db)):
    p = (
        db.query(ArtisanProfile).join(User, ArtisanProfile.user_id == User.id)
        .filter(ArtisanProfile.id == artisan_id, *_visible())
        .options(joinedload(ArtisanProfile.user), joinedload(ArtisanProfile.category),
                 selectinload(ArtisanProfile.locations), selectinload(ArtisanProfile.portfolio))
        .first()
    )
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This artisan could not be found")
    return to_detail(p)


@router.get("/{artisan_id}/reviews", response_model=ReviewListOut)
def artisan_reviews(artisan_id: int, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    p = (db.query(ArtisanProfile).join(User, ArtisanProfile.user_id == User.id)
         .filter(ArtisanProfile.id == artisan_id, *_visible()).first())
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This artisan could not be found")
    q = db.query(Review).filter(Review.artisan_id == p.id).options(joinedload(Review.customer))
    total = q.with_entities(func.count(Review.id)).scalar() or 0
    rows = q.order_by(Review.created_at.desc(), Review.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ReviewListOut(items=[to_review_out(r) for r in rows], total=total, page=page,
                         pages=max(1, math.ceil(total / page_size)), avg_rating=p.avg_rating or 0, review_count=p.review_count or 0)
