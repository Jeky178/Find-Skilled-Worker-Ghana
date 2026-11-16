from sqlalchemy.orm import Session

from models import Notification


def notify(db: Session, user_id: int, title: str, message: str, link: str | None = None) -> None:
    """Queue an in-app notification. The caller commits, so it is saved together with the change that caused it."""
    db.add(Notification(user_id=user_id, title=title[:150], message=message[:500], link=link))
