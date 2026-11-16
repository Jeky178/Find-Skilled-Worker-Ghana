from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_admin
from models import ContactMessage, User
from schemas import ContactMessageIn, ContactMessageOut
from services import rate_limit

router = APIRouter(prefix="/api/contact", tags=["Contact"])

MAX_MESSAGES_PER_HOUR = 5


@router.post("", status_code=status.HTTP_201_CREATED)
def send_message(data: ContactMessageIn, request: Request, db: Session = Depends(get_db)):
    key = f"contact:{request.client.host if request.client else 'unknown'}"
    if rate_limit.is_blocked(key, max_attempts=MAX_MESSAGES_PER_HOUR, window_seconds=3600):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You have sent several messages already. Please try again later.")
    rate_limit.record_failure(key)  # counts every submission toward the hourly limit
    db.add(ContactMessage(**data.model_dump()))
    db.commit()
    return {"detail": "Thank you. Your message has been received."}


@router.get("", response_model=list[ContactMessageOut])
def list_messages(unread_only: bool = False, limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    q = db.query(ContactMessage)
    if unread_only:
        q = q.filter(ContactMessage.is_read.is_(False))
    return q.order_by(ContactMessage.created_at.desc()).limit(min(limit, 500)).all()


@router.patch("/{message_id}/read", response_model=ContactMessageOut)
def mark_read(message_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    msg = db.get(ContactMessage, message_id)
    if msg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    msg.is_read = True
    db.commit()
    db.refresh(msg)
    return msg
