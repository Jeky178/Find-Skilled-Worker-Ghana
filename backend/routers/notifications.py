import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import Notification, User
from schemas import NotificationListOut, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


def _unread(db: Session, user: User) -> int:
    return db.query(func.count(Notification.id)).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).scalar() or 0


@router.get("", response_model=NotificationListOut)
def list_notifications(unread_only: bool = False, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    total = q.with_entities(func.count(Notification.id)).scalar() or 0
    rows = q.order_by(Notification.created_at.desc(), Notification.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return NotificationListOut(items=rows, total=total, unread=_unread(db, user), page=page, pages=max(1, math.ceil(total / page_size)))


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"unread": _unread(db, user)}


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
    if n is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return n
