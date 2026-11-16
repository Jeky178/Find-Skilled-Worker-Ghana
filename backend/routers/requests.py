"""Service requests: create, list, view, change status, review."""
import math
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from dependencies import get_current_user, require_customer
from models import (
    ArtisanProfile, RequestPhoto, RequestStatus, Review, ServiceRequest, User, UserRole,
)
from schemas import RequestDetailOut, RequestListOut, RequestSummary, ReviewCreate, ReviewOut, StatusUpdate
from services.notifications import notify
from services.request_flow import NOTE_REQUIRED, OPEN_STATUSES, can_move
from services.request_views import recompute_rating, to_detail, to_request_out, to_review_out
from services.uploads import delete_image, save_image

router = APIRouter(prefix="/api/requests", tags=["Service requests"])

MAX_PHOTOS = 5
MAX_REQUESTS_PER_DAY = 10
ACTIVE = (RequestStatus.pending, RequestStatus.accepted, RequestStatus.in_progress)


def _query(db: Session):
    return db.query(ServiceRequest).options(
        joinedload(ServiceRequest.customer),
        joinedload(ServiceRequest.artisan).joinedload(ArtisanProfile.user),
        joinedload(ServiceRequest.category),
        selectinload(ServiceRequest.photos),
        joinedload(ServiceRequest.review).joinedload(Review.customer),
    )


def _my_profile(db: Session, user: User) -> ArtisanProfile | None:
    return db.query(ArtisanProfile).filter(ArtisanProfile.user_id == user.id).first()


def _role_in(req: ServiceRequest, user: User) -> str | None:
    if user.role == UserRole.admin:
        return "admin"
    if req.customer_id == user.id:
        return "customer"
    if user.role == UserRole.artisan and req.artisan.user_id == user.id:
        return "artisan"
    return None


def _get_for(db: Session, request_id: int, user: User) -> tuple[ServiceRequest, str]:
    req = _query(db).filter(ServiceRequest.id == request_id).first()
    role = _role_in(req, user) if req else None
    if req is None or role is None:                       # same answer either way: don't reveal that it exists
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
    return req, role


# --------------------------------------------------------------------- create
@router.post("", response_model=RequestDetailOut, status_code=status.HTTP_201_CREATED)
def create_request(
    artisan_id: int = Form(...),
    title: str = Form(..., min_length=3, max_length=150),
    description: str = Form(..., min_length=10, max_length=3000),
    location: str = Form(..., min_length=2, max_length=120),
    preferred_date: date | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    title, description, location = title.strip(), description.strip(), location.strip()
    photos = [f for f in photos if f.filename]
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"You can attach at most {MAX_PHOTOS} photos")
    if preferred_date and preferred_date < date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The preferred date cannot be in the past")

    artisan = (
        db.query(ArtisanProfile).join(User, ArtisanProfile.user_id == User.id)
        .filter(ArtisanProfile.id == artisan_id, User.is_active.is_(True), User.is_suspended.is_(False))
        .options(joinedload(ArtisanProfile.user), joinedload(ArtisanProfile.category)).first()
    )
    if artisan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This artisan could not be found")
    if not artisan.is_available:
        raise HTTPException(status.HTTP_409_CONFLICT, "This artisan is not taking new jobs right now")

    since = datetime.now(timezone.utc) - timedelta(days=1)
    if db.query(func.count(ServiceRequest.id)).filter(ServiceRequest.customer_id == user.id, ServiceRequest.created_at >= since).scalar() >= MAX_REQUESTS_PER_DAY:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You have sent many requests today. Please try again tomorrow")
    duplicate = db.query(ServiceRequest.id).filter(
        ServiceRequest.customer_id == user.id, ServiceRequest.artisan_id == artisan.id,
        func.lower(ServiceRequest.title) == title.lower(), ServiceRequest.status.in_(ACTIVE),
    ).first()
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an open request with this artisan with the same title")

    saved: list[str] = []
    try:
        for f in photos:
            saved.append(save_image(f, "requests"))
    except HTTPException:
        for path in saved:
            delete_image(path)
        raise

    req = ServiceRequest(
        customer_id=user.id, artisan_id=artisan.id, category_id=artisan.category_id, title=title,
        description=description, location=location, preferred_date=preferred_date,
        photos=[RequestPhoto(image_path=p) for p in saved],
    )
    db.add(req)
    db.flush()
    notify(db, artisan.user_id, "New service request",
           f"{user.full_name} needs a {artisan.category.name.lower()} in {location}: {title}", f"/requests/{req.id}")
    db.commit()
    return to_detail(_get_for(db, req.id, user)[0], "customer")


# ---------------------------------------------------------------------- lists
def _scoped(db: Session, user: User):
    q = _query(db)
    if user.role == UserRole.artisan:
        profile = _my_profile(db, user)
        return q.filter(ServiceRequest.artisan_id == (profile.id if profile else -1)), "artisan"
    return q.filter(ServiceRequest.customer_id == user.id), "customer"


@router.get("/mine", response_model=RequestListOut)
def my_requests(
    status_filter: str | None = Query(None, alias="status", description="a status, or 'active' / 'closed'"),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if user.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only customers and artisans have requests")
    q, role = _scoped(db, user)
    if status_filter == "active":
        q = q.filter(ServiceRequest.status.in_(ACTIVE))
    elif status_filter == "closed":
        q = q.filter(~ServiceRequest.status.in_(ACTIVE))
    elif status_filter:
        try:
            q = q.filter(ServiceRequest.status == RequestStatus(status_filter))
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown status filter")
    total = q.with_entities(func.count(ServiceRequest.id)).scalar() or 0
    rows = q.order_by(ServiceRequest.updated_at.desc(), ServiceRequest.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return RequestListOut(items=[to_request_out(r, role) for r in rows], total=total, page=page,
                          pages=max(1, math.ceil(total / page_size)))


@router.get("/summary", response_model=RequestSummary)
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only customers and artisans have requests")
    q, _ = _scoped(db, user)
    counts = dict(q.with_entities(ServiceRequest.status, func.count(ServiceRequest.id)).group_by(ServiceRequest.status).all())
    n = lambda *s: sum(counts.get(x, 0) for x in s)  # noqa: E731
    return RequestSummary(pending=n(RequestStatus.pending), active=n(RequestStatus.accepted, RequestStatus.in_progress),
                          completed=n(RequestStatus.completed), total=sum(counts.values()))


# --------------------------------------------------------------------- detail
@router.get("/{request_id}", response_model=RequestDetailOut)
def get_request(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req, role = _get_for(db, request_id, user)
    return to_detail(req, role)


@router.patch("/{request_id}/status", response_model=RequestDetailOut)
def update_status(request_id: int, data: StatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req, role = _get_for(db, request_id, user)
    if role == "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrators cannot change a request's status")
    if not can_move(role, req.status, data.status):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"A {role} cannot move a request from '{req.status.value}' to '{data.status.value}'")
    if (role, data.status) in NOTE_REQUIRED and not data.note:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please give a short reason")

    req.status = data.status
    req.status_note = data.note
    artisan_name, customer_name = req.artisan.user.full_name, req.customer.full_name
    link = f"/requests/{req.id}"
    target_user = req.customer_id if role == "artisan" else req.artisan.user_id
    actor = artisan_name if role == "artisan" else customer_name
    texts = {
        RequestStatus.accepted: ("Request accepted", f"{actor} accepted your request: {req.title}"),
        RequestStatus.rejected: ("Request declined", f"{actor} could not take your request: {req.title}. Reason: {data.note}"),
        RequestStatus.in_progress: ("Work has started", f"{actor} has started work on: {req.title}"),
        RequestStatus.completed: ("Job completed", f"{actor} marked this job as completed: {req.title}"
                                  + (". Please rate the service." if role == "artisan" else "")),
        RequestStatus.cancelled: ("Request cancelled", f"{actor} cancelled: {req.title}" + (f". Reason: {data.note}" if data.note else "")),
    }
    notify(db, target_user, *texts[data.status], link)
    db.commit()
    db.refresh(req)
    return to_detail(_get_for(db, request_id, user)[0], role)


# --------------------------------------------------------------------- review
@router.post("/{request_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def review_request(request_id: int, data: ReviewCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    req, role = _get_for(db, request_id, user)
    if role != "customer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the customer who made the request can review it")
    if req.status != RequestStatus.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can review a job after it is completed")
    if req.review is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already reviewed this job")

    review = Review(request_id=req.id, customer_id=user.id, artisan_id=req.artisan_id, rating=data.rating, comment=data.comment)
    db.add(review)
    db.flush()
    recompute_rating(db, req.artisan)
    notify(db, req.artisan.user_id, f"New {data.rating}-star review", f"{user.full_name} reviewed your work on: {req.title}", f"/requests/{req.id}")
    db.commit()
    db.refresh(review)
    return to_review_out(review)
