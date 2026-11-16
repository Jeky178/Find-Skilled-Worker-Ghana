from sqlalchemy.orm import Session

from models import AdminAction, User


def log_action(db: Session, admin: User, action: str, target_type: str, target_id: int | None = None, detail: str | None = None) -> None:
    """Record an admin action. The caller commits, so the log is saved together with the change itself."""
    db.add(AdminAction(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, detail=(detail or "")[:500] or None))
