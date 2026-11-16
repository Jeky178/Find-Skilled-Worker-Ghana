"""
Create an admin account, or reset the password of an existing one, then PROVE the login works.

    python create_admin.py

Run it from the backend folder. Safe to run again: it updates the existing account.
It also lists every admin currently in the database so you can see the exact email to use.
"""
import getpass
import sys

from auth import hash_password, verify_password
from database import Base, SessionLocal, engine
from models import User, UserRole
from schemas import RegisterRequest


def _ask_password() -> str:
    if sys.stdin.isatty():
        try:
            return getpass.getpass("Admin password (typing is hidden): ")
        except Exception:
            pass
    print("(Your terminal cannot hide typing, so the password will be visible.)")
    return input("Admin password: ")


def run(db) -> None:
    admins = db.query(User).filter(User.role == UserRole.admin).all()
    if admins:
        print("Admin accounts already in the database:")
        for a in admins:
            print(f"  - {a.email}  (active={a.is_active}, suspended={a.is_suspended})")
    else:
        print("No admin account exists yet.")

    email = input("\nAdmin email: ").strip().lower()
    name = input("Admin full name (press Enter to keep current): ").strip()
    password = _ask_password().strip()

    try:  # reuse the same rules as registration
        RegisterRequest(full_name=name or "Administrator", email=email, password=password)
    except Exception as exc:
        errors = getattr(exc, "errors", lambda: [])()
        for e in errors:
            print("  Problem:", str(e.get("msg", "")).removeprefix("Value error, "))
        sys.exit("\nNothing was saved. Fix the problem above and run the script again.")

    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = UserRole.admin
        user.password_hash = hash_password(password)
        user.is_active, user.is_suspended = True, False
        if name:
            user.full_name = name
        action = "updated (password reset)"
    else:
        user = User(full_name=name or "Administrator", email=email, password_hash=hash_password(password), role=UserRole.admin)
        db.add(user)
        action = "created"
    db.commit()

    db.refresh(user)
    ok = verify_password(password, user.password_hash)
    print(f"\nAdmin {action}: {user.email}")
    print("Login check:", "PASSED. You can log in with these details." if ok else "FAILED")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        run(session)
