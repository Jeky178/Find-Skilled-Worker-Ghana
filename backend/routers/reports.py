"""Customers and artisans report problems. Admins handle them in /api/admin/reports."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
from dependencies import get_current_user
from models import ArtisanProfile, Report, ReportStatus, ServiceRequest, User, UserRole
from schemas_admin import REPORT_REASONS, ReportIn
from services.notifications import notify

router = APIRouter(prefix="/api/reports", tags=["Reports"])

MAX_REPORTS_PER_DAY = 5


@router.get("/reasons")
def reasons():
    return REPORT_REASONS


@router.post("", status_code=status.HTTP_201_CREATED)
def file_report(data: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrators review reports, they do not file them")
    if (data.artisan_id is None) == (data.request_id is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Report either an artisan or a service request")

    request_id = None
    if data.artisan_id is not None:
        profile = db.query(ArtisanProfile).filter(ArtisanProfile.id == data.artisan_id).first()
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Artisan not found")
        reported_id = profile.user_id
    else:
        req = (db.query(ServiceRequest).options(joinedload(ServiceRequest.artisan)).filter(ServiceRequest.id == data.request_id).first())
        mine = req and (req.customer_id == user.id or req.artisan.user_id == user.id)
        if not mine:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service request not found")
        reported_id = req.artisan.user_id if req.customer_id == user.id else req.customer_id
        request_id = req.id

    if reported_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot report yourself")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    if db.query(func.count(Report.id)).filter(Report.reporter_id == user.id, Report.created_at >= since).scalar() >= MAX_REPORTS_PER_DAY:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You have sent several reports today. Please try again tomorrow")
    if db.query(Report.id).filter(Report.reporter_id == user.id, Report.reported_user_id == reported_id, Report.reason == data.reason,
                                  Report.status.in_((ReportStatus.open, ReportStatus.reviewing))).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already reported this for the same reason. We are looking into it")

    report = Report(reporter_id=user.id, reported_user_id=reported_id, request_id=request_id, reason=data.reason, details=data.details)
    db.add(report)
    for admin_id in [a for (a,) in db.query(User.id).filter(User.role == UserRole.admin, User.is_active.is_(True)).all()]:
        notify(db, admin_id, "New report", f"{user.full_name} reported a user: {data.reason}", "/admin/reports")
    db.commit()
    return {"detail": "Thank you. Our team will review your report."}
