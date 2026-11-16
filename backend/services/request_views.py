"""Builds API shapes for service requests and reviews."""
from decimal import Decimal
from urllib.parse import quote

from models import ArtisanProfile, Review, ServiceRequest, User
from schemas import ContactInfo, PersonMini, RequestDetailOut, RequestOut, ReviewOut
from services.request_flow import CONTACT_VISIBLE, allowed_actions


def short_name(full_name: str) -> str:
    parts = full_name.split()
    return full_name if len(parts) < 2 else f"{parts[0]} {parts[-1][0]}."


def artisan_person(p: ArtisanProfile) -> PersonMini:
    return PersonMini(id=p.id, name=p.user.full_name, profile_image=p.profile_image)


def customer_person(u: User) -> PersonMini:
    return PersonMini(name=u.full_name)


def to_request_out(r: ServiceRequest, viewer_role: str) -> RequestOut:
    other = customer_person(r.customer) if viewer_role == "artisan" else artisan_person(r.artisan)
    return RequestOut(
        id=r.id, title=r.title, status=r.status, category=r.category.name, location=r.location,
        preferred_date=r.preferred_date, created_at=r.created_at, updated_at=r.updated_at,
        other_party=other, photo_count=len(r.photos), has_review=r.review is not None,
    )


def to_review_out(rv: Review, include_job: bool = False) -> ReviewOut:
    return ReviewOut(
        id=rv.id, rating=rv.rating, comment=rv.comment, created_at=rv.created_at,
        reviewer_name=short_name(rv.customer.full_name),
        category=rv.request.category.name if include_job else None,
        artisan_name=rv.artisan.user.full_name if include_job else None,
    )


def _wa(number: str | None, text: str) -> str | None:
    return f"https://wa.me/{number}?text={quote(text)}" if number else None


def to_detail(r: ServiceRequest, viewer_role: str) -> RequestDetailOut:
    contact = None
    if viewer_role == "customer":
        a = r.artisan
        contact = ContactInfo(name=a.user.full_name, phone=a.phone,
                              whatsapp_url=_wa(a.whatsapp_number, f"Hello {a.user.full_name}, about my request: {r.title}"))
    elif viewer_role == "artisan" and r.status in CONTACT_VISIBLE:      # customer's number is shared only after accepting
        c = r.customer
        contact = ContactInfo(name=c.full_name, phone=c.phone,
                              whatsapp_url=_wa(c.phone, f"Hello {c.full_name}, about your request: {r.title}"))
    return RequestDetailOut(
        id=r.id, title=r.title, description=r.description, status=r.status, status_note=r.status_note,
        category=r.category.name, location=r.location, preferred_date=r.preferred_date,
        created_at=r.created_at, updated_at=r.updated_at,
        photos=[p.image_path for p in sorted(r.photos, key=lambda x: x.id)],
        viewer_role=viewer_role, allowed_actions=allowed_actions(viewer_role, r.status) if viewer_role != "admin" else [],
        artisan=artisan_person(r.artisan), customer=customer_person(r.customer), other_contact=contact,
        review=to_review_out(r.review) if r.review else None,
    )


def recompute_rating(db, artisan: ArtisanProfile) -> None:
    from sqlalchemy import func
    avg, count = db.query(func.avg(Review.rating), func.count(Review.id)).filter(Review.artisan_id == artisan.id).one()
    artisan.avg_rating = round(Decimal(str(avg or 0)), 2)
    artisan.review_count = count or 0
