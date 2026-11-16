import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
from dependencies import get_current_user
from models import ArtisanProfile, Review, ServiceRequest, User, UserRole
from schemas import ReviewListOut
from services.request_views import to_review_out

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.get("/mine", response_model=ReviewListOut)
def my_reviews(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Customers: reviews they wrote. Artisans: reviews they received."""
    if user.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrators do not have reviews")
    q = db.query(Review).options(
        joinedload(Review.customer), joinedload(Review.artisan).joinedload(ArtisanProfile.user),
        joinedload(Review.request).joinedload(ServiceRequest.category),
    )
    avg, count = 0, 0
    if user.role == UserRole.artisan:
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()
        q = q.filter(Review.artisan_id == (profile.id if profile else -1))
        if profile:
            avg, count = profile.avg_rating, profile.review_count
    else:
        q = q.filter(Review.customer_id == user.id)
    total = q.with_entities(func.count(Review.id)).scalar() or 0
    rows = q.order_by(Review.created_at.desc(), Review.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ReviewListOut(items=[to_review_out(r, include_job=True) for r in rows], total=total, page=page,
                         pages=max(1, math.ceil(total / page_size)), avg_rating=avg or 0, review_count=count or total)
