"""Administrator tools. Every endpoint here requires the admin role."""
import math
import re
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from database import get_db
from dependencies import require_admin
from models import (
    AdminAction, ArtisanProfile, ContactMessage, Payment, PaymentItem, PaymentPurpose, PaymentStatus, PlanType, Subscription, SubscriptionStatus, Report, ReportStatus, RequestStatus, Review,
    ServiceCategory, ServiceRequest, User, UserRole, Verification, VerificationStatus,
)
from schemas_billing import AdminPaymentList, AdminPaymentOut
from schemas_admin import (
    ActivityItem, AdminRequestList, AdminRequestOut, AdminStats, AdminUserList, AdminUserOut, CategoryAdminOut,
    CategoryIn, CategoryPatch, DecisionIn, FeatureIn, PlanIn, ReportAdminOut, ReportListOut, ReportUpdate,
    SuspendIn, VerificationAdminOut, VerificationListOut,
)
from services.artisan_views import featured_active
from services.audit import log_action
from services.notifications import notify
from services.uploads import read_private_image

router = APIRouter(prefix="/api/admin", tags=["Administration"], dependencies=[Depends(require_admin)])


def _pages(total: int, size: int) -> int:
    return max(1, math.ceil(total / size))


def _like(value: str) -> str:
    return "%" + value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------- stats
@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db)):
    count = lambda model, *f: db.query(func.count(model.id)).filter(*f).scalar() or 0  # noqa: E731
    by_role = dict(db.query(User.role, func.count(User.id)).group_by(User.role).all())
    by_ver = dict(db.query(ArtisanProfile.verification_status, func.count(ArtisanProfile.id)).group_by(ArtisanProfile.verification_status).all())
    by_req = dict(db.query(ServiceRequest.status, func.count(ServiceRequest.id)).group_by(ServiceRequest.status).all())
    S = RequestStatus
    week = datetime.now(timezone.utc) - timedelta(days=7)
    return AdminStats(
        customers=by_role.get(UserRole.customer, 0), artisans=by_role.get(UserRole.artisan, 0), admins=by_role.get(UserRole.admin, 0),
        suspended_users=count(User, User.is_suspended.is_(True)), new_users_7d=count(User, User.created_at >= week),
        verification_unverified=by_ver.get(VerificationStatus.unverified, 0), verification_pending=by_ver.get(VerificationStatus.pending, 0),
        verification_approved=by_ver.get(VerificationStatus.approved, 0), verification_rejected=by_ver.get(VerificationStatus.rejected, 0),
        featured_artisans=count(ArtisanProfile, ArtisanProfile.is_featured.is_(True)), premium_artisans=count(ArtisanProfile, ArtisanProfile.plan == PlanType.premium),
        requests_total=sum(by_req.values()), requests_pending=by_req.get(S.pending, 0),
        requests_active=by_req.get(S.accepted, 0) + by_req.get(S.in_progress, 0), requests_completed=by_req.get(S.completed, 0),
        requests_closed=by_req.get(S.cancelled, 0) + by_req.get(S.rejected, 0), reviews_total=count(Review),
        open_reports=count(Report, Report.status.in_((ReportStatus.open, ReportStatus.reviewing))),
        unread_messages=count(ContactMessage, ContactMessage.is_read.is_(False)),
        revenue_ghs=db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == PaymentStatus.completed).scalar(),
        payments_pending=count(Payment, Payment.status == PaymentStatus.pending),
        active_premium=count(Subscription, Subscription.status == SubscriptionStatus.active, Subscription.ends_at > datetime.now(timezone.utc)),
    )


# ---------------------------------------------------------------------- users
def _user_out(u: User) -> AdminUserOut:
    p = u.artisan_profile
    return AdminUserOut(
        id=u.id, full_name=u.full_name, email=u.email, phone=u.phone, role=u.role, is_active=u.is_active,
        is_suspended=u.is_suspended, suspended_reason=u.suspended_reason, created_at=u.created_at,
        artisan_id=p.id if p else None, category=p.category.name if p else None,
        verification_status=p.verification_status if p else None, plan=p.plan if p else None,
        is_featured=featured_active(p) if p else None, featured_until=p.featured_until if p else None,
    )


@router.get("/users", response_model=AdminUserList)
def list_users(
    role: UserRole | None = None, q: str | None = Query(None, max_length=100), state: str | None = Query(None, pattern="^(active|suspended)$"),
    verification: VerificationStatus | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(User).options(joinedload(User.artisan_profile).joinedload(ArtisanProfile.category))
    if role:
        query = query.filter(User.role == role)
    if q and q.strip():
        query = query.filter(or_(User.full_name.ilike(_like(q), escape="\\"), User.email.ilike(_like(q), escape="\\")))
    if state == "suspended":
        query = query.filter(User.is_suspended.is_(True))
    elif state == "active":
        query = query.filter(User.is_suspended.is_(False))
    if verification:
        query = query.filter(User.artisan_profile.has(ArtisanProfile.verification_status == verification))
    total = query.with_entities(func.count(User.id)).scalar() or 0
    rows = query.order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return AdminUserList(items=[_user_out(u) for u in rows], total=total, page=page, pages=_pages(total, page_size))


def _target_user(db: Session, user_id: int) -> User:
    u = db.query(User).options(joinedload(User.artisan_profile).joinedload(ArtisanProfile.category)).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return u


@router.post("/users/{user_id}/suspend", response_model=AdminUserOut)
def suspend_user(user_id: int, data: SuspendIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = _target_user(db, user_id)
    if u.id == admin.id or u.role == UserRole.admin:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Administrator accounts cannot be suspended")
    u.is_suspended, u.suspended_reason = True, data.reason
    log_action(db, admin, "suspend_user", "user", u.id, f"{u.email}: {data.reason}")
    db.commit()
    return _user_out(u)


@router.post("/users/{user_id}/unsuspend", response_model=AdminUserOut)
def unsuspend_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = _target_user(db, user_id)
    u.is_suspended, u.suspended_reason = False, None
    log_action(db, admin, "unsuspend_user", "user", u.id, u.email)
    db.commit()
    return _user_out(u)


# ----------------------------------------------- featured listings and plans
@router.post("/artisans/{profile_id}/feature")
def set_featured(profile_id: int, data: FeatureIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(ArtisanProfile).options(joinedload(ArtisanProfile.user)).filter(ArtisanProfile.id == profile_id).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan not found")
    until = None
    if data.featured and data.until:
        until = datetime.combine(data.until, time(23, 59, 59), tzinfo=timezone.utc)
        if until <= datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The end date must be in the future")
    p.is_featured, p.featured_until = data.featured, until
    log_action(db, admin, "feature_artisan" if data.featured else "unfeature_artisan", "artisan", p.id,
               f"{p.user.full_name}" + (f" until {data.until}" if until else ""))
    db.commit()
    return {"artisan_id": p.id, "is_featured": p.is_featured, "featured_until": p.featured_until}


@router.post("/artisans/{profile_id}/plan")
def set_plan(profile_id: int, data: PlanIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Complimentary plan change by an admin. This records NO payment: paid plans arrive with the payment provider."""
    p = db.query(ArtisanProfile).options(joinedload(ArtisanProfile.user)).filter(ArtisanProfile.id == profile_id).first()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan not found")
    p.plan = data.plan
    log_action(db, admin, "set_plan", "artisan", p.id, f"{p.user.full_name}: {data.plan.value} (complimentary, no payment)")
    db.commit()
    return {"artisan_id": p.id, "plan": p.plan}


# --------------------------------------------------------------- verification
def _ver_out(v: Verification) -> VerificationAdminOut:
    a = v.artisan
    return VerificationAdminOut(
        id=v.id, status=v.status, id_type=v.id_type, created_at=v.created_at, reviewed_at=v.reviewed_at, admin_note=v.admin_note,
        artisan_id=a.id, artisan_name=a.user.full_name, artisan_email=a.user.email, category=a.category.name,
        has_certificate=bool(v.trade_certificate_path),
    )


@router.get("/verifications", response_model=VerificationListOut)
def list_verifications(status_filter: VerificationStatus | None = Query(None, alias="status"), page: int = Query(1, ge=1),
                       page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    q = db.query(Verification).options(joinedload(Verification.artisan).joinedload(ArtisanProfile.user),
                                       joinedload(Verification.artisan).joinedload(ArtisanProfile.category))
    if status_filter:
        q = q.filter(Verification.status == status_filter)
    total = q.with_entities(func.count(Verification.id)).scalar() or 0
    # oldest first for the pending queue, so nobody waits forever
    order = Verification.created_at.asc() if status_filter == VerificationStatus.pending else Verification.created_at.desc()
    rows = q.order_by(order, Verification.id).offset((page - 1) * page_size).limit(page_size).all()
    return VerificationListOut(items=[_ver_out(v) for v in rows], total=total, page=page, pages=_pages(total, page_size))


@router.get("/verifications/{vid}/document")
def verification_document(vid: int, kind: str = Query("id", pattern="^(id|certificate)$"), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    v = db.get(Verification, vid)
    key = None if v is None else (v.document_path if kind == "id" else v.trade_certificate_path)
    if v is None or not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    image_bytes = read_private_image(key)
    if image_bytes is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This document is unavailable. The artisan may need to upload it again.",
        )
    log_action(db, admin, "view_verification_document", "verification", vid, kind)
    db.commit()
    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.post("/verifications/{vid}/decision", response_model=VerificationAdminOut)
def decide_verification(vid: int, data: DecisionIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    v = (db.query(Verification).options(joinedload(Verification.artisan).joinedload(ArtisanProfile.user),
                                        joinedload(Verification.artisan).joinedload(ArtisanProfile.category))
         .filter(Verification.id == vid).first())
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if v.status != VerificationStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This application has already been reviewed")
    if not data.approve and not data.note:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please explain why the application was rejected")

    new = VerificationStatus.approved if data.approve else VerificationStatus.rejected
    v.status, v.admin_note, v.reviewed_by_id, v.reviewed_at = new, data.note, admin.id, datetime.now(timezone.utc)
    v.artisan.verification_status = new
    if data.approve:
        notify(db, v.artisan.user_id, "You are verified", "Your identity has been verified. Your profile now shows the Verified badge.", "/dashboard/verification")
    else:
        notify(db, v.artisan.user_id, "Verification not approved", f"Your application was not approved. Reason: {data.note}. You can apply again.", "/dashboard/verification")
    log_action(db, admin, "approve_verification" if data.approve else "reject_verification", "verification", v.id, v.artisan.user.full_name)
    db.commit()
    return _ver_out(v)


# ------------------------------------------------------------------ categories
def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "category"


def _cat_out(db: Session, c: ServiceCategory) -> CategoryAdminOut:
    n = db.query(func.count(ArtisanProfile.id)).filter(ArtisanProfile.category_id == c.id).scalar() or 0
    return CategoryAdminOut(id=c.id, name=c.name, slug=c.slug, description=c.description, icon=c.icon, is_active=c.is_active, artisan_count=n)


@router.get("/categories", response_model=list[CategoryAdminOut])
def list_categories(db: Session = Depends(get_db)):
    return [_cat_out(db, c) for c in db.query(ServiceCategory).order_by(ServiceCategory.name).all()]


@router.post("/categories", response_model=CategoryAdminOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    slug = _slugify(data.name)
    if db.query(ServiceCategory).filter(or_(func.lower(ServiceCategory.name) == data.name.lower(), ServiceCategory.slug == slug)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    c = ServiceCategory(name=data.name, slug=slug, description=data.description, icon=data.icon)
    db.add(c)
    db.flush()
    log_action(db, admin, "create_category", "category", c.id, c.name)
    db.commit()
    return _cat_out(db, c)


@router.patch("/categories/{category_id}", response_model=CategoryAdminOut)
def update_category(category_id: int, data: CategoryPatch, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = db.get(ServiceCategory, category_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") and changes["name"].lower() != c.name.lower():
        if db.query(ServiceCategory).filter(func.lower(ServiceCategory.name) == changes["name"].lower(), ServiceCategory.id != c.id).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    for k, v in changes.items():
        if k == "is_active" and v is None:
            continue
        setattr(c, k, v if k != "name" or v else c.name)   # the slug never changes, so links keep working
    log_action(db, admin, "update_category", "category", c.id, f"{c.name} ({', '.join(changes)})")
    db.commit()
    return _cat_out(db, c)


# --------------------------------------------------------- request monitoring
@router.get("/requests", response_model=AdminRequestList)
def monitor_requests(status_filter: RequestStatus | None = Query(None, alias="status"), q: str | None = Query(None, max_length=100),
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(ServiceRequest).options(joinedload(ServiceRequest.customer), joinedload(ServiceRequest.category),
                                             joinedload(ServiceRequest.artisan).joinedload(ArtisanProfile.user))
    if status_filter:
        query = query.filter(ServiceRequest.status == status_filter)
    if q and q.strip():
        query = query.filter(ServiceRequest.title.ilike(_like(q), escape="\\"))
    total = query.with_entities(func.count(ServiceRequest.id)).scalar() or 0
    rows = query.order_by(ServiceRequest.updated_at.desc(), ServiceRequest.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [AdminRequestOut(id=r.id, title=r.title, status=r.status, category=r.category.name, location=r.location,
                             customer_name=r.customer.full_name, artisan_name=r.artisan.user.full_name,
                             created_at=r.created_at, updated_at=r.updated_at) for r in rows]
    return AdminRequestList(items=items, total=total, page=page, pages=_pages(total, page_size))


# -------------------------------------------------------------------- reports
def _report_out(r: Report) -> ReportAdminOut:
    return ReportAdminOut(
        id=r.id, status=r.status, reason=r.reason, details=r.details, admin_note=r.admin_note, created_at=r.created_at,
        reporter_name=r.reporter.full_name, reported_user_id=r.reported_user_id, reported_name=r.reported_user.full_name,
        reported_role=r.reported_user.role, reported_suspended=r.reported_user.is_suspended,
        request_id=r.request_id, request_title=None,
    )


@router.get("/reports", response_model=ReportListOut)
def list_reports(status_filter: ReportStatus | None = Query(None, alias="status"), page: int = Query(1, ge=1),
                 page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    q = db.query(Report).options(joinedload(Report.reporter), joinedload(Report.reported_user))
    if status_filter:
        q = q.filter(Report.status == status_filter)
    total = q.with_entities(func.count(Report.id)).scalar() or 0
    rows = q.order_by(Report.created_at.desc(), Report.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    titles = {}
    ids = [r.request_id for r in rows if r.request_id]
    if ids:
        titles = dict(db.query(ServiceRequest.id, ServiceRequest.title).filter(ServiceRequest.id.in_(ids)).all())
    items = []
    for r in rows:
        out = _report_out(r)
        out.request_title = titles.get(r.request_id)
        items.append(out)
    return ReportListOut(items=items, total=total, page=page, pages=_pages(total, page_size))


@router.patch("/reports/{report_id}", response_model=ReportAdminOut)
def update_report(report_id: int, data: ReportUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.query(Report).options(joinedload(Report.reporter), joinedload(Report.reported_user)).filter(Report.id == report_id).first()
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    closing = data.status in (ReportStatus.resolved, ReportStatus.dismissed)
    if closing and not data.admin_note:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please add a short note explaining the outcome")
    was_closed = r.status in (ReportStatus.resolved, ReportStatus.dismissed)
    r.status, r.admin_note = data.status, data.admin_note
    r.resolved_by_id = admin.id if closing else None
    if closing and not was_closed:
        notify(db, r.reporter_id, "Your report was reviewed", f"Thank you for reporting {r.reported_user.full_name}. Outcome: {data.admin_note}")
    log_action(db, admin, f"report_{data.status.value}", "report", r.id, r.reported_user.full_name)
    db.commit()
    return _report_out(r)


# ------------------------------------------------------------------- activity
@router.get("/activity", response_model=list[ActivityItem])
def activity(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    """A merged, newest-first feed of what is happening on the platform."""
    n = limit
    items: list[ActivityItem] = []
    for u in db.query(User).order_by(User.created_at.desc()).limit(n):
        items.append(ActivityItem(kind="user", text=f"New {u.role.value} registered: {u.full_name}", at=u.created_at, link="/admin/users"))
    for r in (db.query(ServiceRequest).options(joinedload(ServiceRequest.customer), joinedload(ServiceRequest.artisan).joinedload(ArtisanProfile.user))
              .order_by(ServiceRequest.created_at.desc()).limit(n)):
        items.append(ActivityItem(kind="request", text=f"{r.customer.full_name} requested {r.artisan.user.full_name}: {r.title}", at=r.created_at, link=f"/requests/{r.id}"))
    for rv in db.query(Review).options(joinedload(Review.customer), joinedload(Review.artisan).joinedload(ArtisanProfile.user)).order_by(Review.created_at.desc()).limit(n):
        items.append(ActivityItem(kind="review", text=f"{rv.customer.full_name} gave {rv.artisan.user.full_name} {rv.rating} stars", at=rv.created_at))
    for rp in db.query(Report).options(joinedload(Report.reporter), joinedload(Report.reported_user)).order_by(Report.created_at.desc()).limit(n):
        items.append(ActivityItem(kind="report", text=f"{rp.reporter.full_name} reported {rp.reported_user.full_name}: {rp.reason}", at=rp.created_at, link="/admin/reports"))
    for v in db.query(Verification).options(joinedload(Verification.artisan).joinedload(ArtisanProfile.user)).order_by(Verification.created_at.desc()).limit(n):
        items.append(ActivityItem(kind="verification", text=f"{v.artisan.user.full_name} applied for verification", at=v.created_at, link="/admin/verifications"))
    for a in db.query(AdminAction).options(joinedload(AdminAction.admin)).order_by(AdminAction.created_at.desc()).limit(n):
        items.append(ActivityItem(kind="admin", text=f"{a.admin.full_name}: {a.action.replace('_', ' ')}" + (f" ({a.detail})" if a.detail else ""), at=a.created_at))
    items.sort(key=lambda i: _utc(i.at), reverse=True)
    return items[:limit]


# ------------------------------------------------------------------- payments
@router.get("/payments", response_model=AdminPaymentList)
def list_payments(status_filter: PaymentStatus | None = Query(None, alias="status"), purpose: PaymentPurpose | None = None,
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Read-only. Admins cannot mark a payment as paid: only the payment provider's confirmation can do that."""
    q = (db.query(Payment, PaymentItem, User).join(PaymentItem, PaymentItem.payment_id == Payment.id).join(User, User.id == Payment.user_id))
    if status_filter:
        q = q.filter(Payment.status == status_filter)
    if purpose:
        q = q.filter(Payment.purpose == purpose)
    total = q.with_entities(func.count(Payment.id)).scalar() or 0
    rows = q.order_by(Payment.created_at.desc(), Payment.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == PaymentStatus.completed).scalar()
    done = db.query(func.count(Payment.id)).filter(Payment.status == PaymentStatus.completed).scalar() or 0
    items = [AdminPaymentOut(id=p.id, reference=p.reference, user_name=u.full_name, user_email=u.email, product_code=i.product_code,
                             purpose=p.purpose, amount=p.amount, currency=p.currency, status=p.status, provider=p.provider,
                             created_at=p.created_at, paid_at=p.paid_at, fulfilled=i.fulfilled_at is not None) for p, i, u in rows]
    return AdminPaymentList(items=items, total=total, page=page, pages=_pages(total, page_size), revenue_ghs=revenue, completed_count=done)
