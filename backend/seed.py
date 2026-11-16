"""
Seed the database.

  python seed.py                         -> create tables + service categories
  python seed.py --admin                 -> also create an admin (prompts for email & password)
  python seed.py --demo                  -> also add DEMO customers/artisans (development only)
  python seed.py --remove-demo           -> delete every demo account and everything attached to it
"""
import argparse
import getpass
import sys

from auth import hash_password
from config import get_settings
from database import Base, SessionLocal, engine
from models import (
    ArtisanLocation, ArtisanProfile, PlanType, ServiceCategory, User, UserRole, VerificationStatus,
)
from schemas import RegisterRequest

CATEGORIES = [
    ("Plumber", "plumber", "Pipe repairs, leaks, installations", "wrench"),
    ("Electrician", "electrician", "Wiring, fittings, repairs", "zap"),
    ("Carpenter", "carpenter", "Furniture, doors, roofing timber", "hammer"),
    ("Painter", "painter", "Interior and exterior painting", "paintbrush"),
    ("Mechanic", "mechanic", "Vehicle repair and servicing", "car"),
    ("AC Technician", "ac-technician", "Air-conditioner installation and repair", "snowflake"),
    ("Refrigeration Technician", "refrigeration-technician", "Fridge and freezer repair", "refrigerator"),
    ("Tiler", "tiler", "Floor and wall tiling", "layout-grid"),
    ("Welder", "welder", "Gates, burglar-proof, metal fabrication", "flame"),
    ("POP Ceiling Installer", "pop-ceiling-installer", "POP and ceiling design", "home"),
    ("Cleaner", "cleaner", "Home and office cleaning", "sparkles"),
    ("Appliance Repair Technician", "appliance-repair", "TVs, washing machines, microwaves", "settings"),
]

# DEMO DATA ONLY: invented people with invented numbers. All start UNVERIFIED with no reviews.
DEMO_ARTISANS = [
    ("Kwame Mensah", "kwame.demo@example.com", "plumber", ["Madina", "Adenta"], 8, 80, 300),
    ("Yaw Boateng", "yaw.demo@example.com", "electrician", ["Dome", "Haatso", "Achimota"], 6, 100, 400),
    ("Kofi Owusu", "kofi.demo@example.com", "carpenter", ["East Legon", "Madina"], 12, 150, 800),
    ("Ama Serwaa", "ama.demo@example.com", "painter", ["Kasoa", "Achimota"], 5, 120, 600),
    ("Samuel Tetteh", "samuel.demo@example.com", "ac-technician", ["East Legon", "Haatso", "Dome"], 9, 120, 500),
    ("Nana Addo Asare", "nana.demo@example.com", "welder", ["Kasoa", "Adenta"], 10, 200, 1200),
]
DEMO_PASSWORD = "Demo1234"


def seed_categories(db):
    existing = {c.slug for c in db.query(ServiceCategory).all()}
    new = [ServiceCategory(name=n, slug=s, description=d, icon=i) for n, s, d, i in CATEGORIES if s not in existing]
    db.add_all(new)
    db.commit()
    print(f"Categories: {len(new)} added, {len(existing)} already present.")


def create_admin(db):
    import create_admin as tool
    tool.run(db)


def remove_demo(db):
    """Delete demo users plus the jobs, reviews and reports attached to them, in a safe order."""
    from models import Notification, Payment, PaymentItem, Report, RequestPhoto, Review, ServiceRequest, Subscription

    users = db.query(User).filter(User.email.like("%.demo@example.com")).all()
    if not users:
        print("No demo accounts found.")
        return
    uids = [u.id for u in users]
    pids = [pid for (pid,) in db.query(ArtisanProfile.id).filter(ArtisanProfile.user_id.in_(uids)).all()]
    reqs = [r for (r,) in db.query(ServiceRequest.id).filter((ServiceRequest.customer_id.in_(uids)) | (ServiceRequest.artisan_id.in_(pids or [-1]))).all()]
    if reqs:
        db.query(Review).filter(Review.request_id.in_(reqs)).delete(synchronize_session=False)
        db.query(Report).filter(Report.request_id.in_(reqs)).delete(synchronize_session=False)
        db.query(RequestPhoto).filter(RequestPhoto.request_id.in_(reqs)).delete(synchronize_session=False)
        db.query(ServiceRequest).filter(ServiceRequest.id.in_(reqs)).delete(synchronize_session=False)
    db.query(Review).filter(Review.customer_id.in_(uids)).delete(synchronize_session=False)
    db.query(Report).filter((Report.reporter_id.in_(uids)) | (Report.reported_user_id.in_(uids))).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id.in_(uids)).delete(synchronize_session=False)
    pay_ids = [i for (i,) in db.query(Payment.id).filter(Payment.user_id.in_(uids)).all()]
    if pay_ids:
        db.query(PaymentItem).filter(PaymentItem.payment_id.in_(pay_ids)).delete(synchronize_session=False)
        db.query(Payment).filter(Payment.id.in_(pay_ids)).delete(synchronize_session=False)
    db.query(Subscription).filter(Subscription.user_id.in_(uids)).delete(synchronize_session=False)
    for u in users:
        db.delete(u)                      # cascades to the artisan profile, areas, portfolio and verifications
    db.commit()
    print(f"Removed {len(users)} demo account(s) and their related data.")


def seed_demo(db):
    if get_settings().ENVIRONMENT == "production":
        sys.exit("Refusing to add demo data when ENVIRONMENT=production.")
    cats = {c.slug: c for c in db.query(ServiceCategory).all()}
    added = 0
    for name, email, slug, locs, years, pmin, pmax in DEMO_ARTISANS:
        if db.query(User).filter(User.email == email).first():
            continue
        user = User(full_name=name, email=email, password_hash=hash_password(DEMO_PASSWORD), role=UserRole.artisan)
        db.add(user)
        db.flush()
        db.add(ArtisanProfile(
            user_id=user.id, category_id=cats[slug].id, years_experience=years,
            headline=f"{cats[slug].name} serving {', '.join(locs)}",
            bio="DEMO PROFILE: sample data for testing the platform.",
            price_min=pmin, price_max=pmax, price_note="Indicative price per job (GH₵)",
            verification_status=VerificationStatus.unverified, plan=PlanType.free,
            locations=[ArtisanLocation(location=l) for l in locs],
        ))
        added += 1
    if not db.query(User).filter(User.email == "customer.demo@example.com").first():
        db.add(User(full_name="Abena Demo", email="customer.demo@example.com",
                    password_hash=hash_password(DEMO_PASSWORD), role=UserRole.customer))
        added += 1
    db.commit()
    print(f"Demo users added: {added} (password for all: {DEMO_PASSWORD}). They are NOT verified.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--remove-demo", action="store_true")
    args = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_categories(db)
        if args.admin:
            create_admin(db)
        if args.demo:
            seed_demo(db)
        if args.remove_demo:
            remove_demo(db)
