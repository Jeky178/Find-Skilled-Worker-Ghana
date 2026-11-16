"""Turns database rows into the public/private artisan shapes the API returns."""
from datetime import datetime, timezone
from urllib.parse import quote

from models import ArtisanProfile, VerificationStatus
from schemas import ArtisanCardOut, ArtisanDetailOut, CategoryMini, MyProfileOut, PortfolioOut
from services.plans import portfolio_limit


def featured_active(p: ArtisanProfile) -> bool:
    """Featured status that respects the expiry date set by an admin."""
    if not p.is_featured:
        return False
    if p.featured_until is None:
        return True
    until = p.featured_until if p.featured_until.tzinfo else p.featured_until.replace(tzinfo=timezone.utc)
    return until > datetime.now(timezone.utc)


def to_card_dict(p: ArtisanProfile) -> dict:
    return dict(
        id=p.id, name=p.user.full_name, headline=p.headline,
        category=CategoryMini.model_validate(p.category), profile_image=p.profile_image,
        locations=sorted(l.location for l in p.locations),
        price_min=p.price_min, price_max=p.price_max, price_note=p.price_note,
        avg_rating=p.avg_rating or 0, review_count=p.review_count or 0,
        years_experience=p.years_experience, is_available=p.is_available,
        verification_status=p.verification_status, plan=p.plan, is_featured=featured_active(p),
    )


def to_card(p: ArtisanProfile) -> ArtisanCardOut:
    return ArtisanCardOut(**to_card_dict(p))


def whatsapp_url(p: ArtisanProfile) -> str | None:
    if not p.whatsapp_number:
        return None
    text = f"Hello {p.user.full_name}, I found your profile on Find a Skilled Worker Ghana and I need a {p.category.name.lower()}."
    return f"https://wa.me/{p.whatsapp_number}?text={quote(text)}"


def to_detail_dict(p: ArtisanProfile) -> dict:
    d = to_card_dict(p)
    d.update(
        bio=p.bio, phone=p.phone, whatsapp_url=whatsapp_url(p),
        portfolio=[PortfolioOut(id=i.id, image_url=i.image_path, caption=i.caption)
                   for i in sorted(p.portfolio, key=lambda x: x.id, reverse=True)],
        member_since=p.created_at,
    )
    return d


def to_detail(p: ArtisanProfile) -> ArtisanDetailOut:
    return ArtisanDetailOut(**to_detail_dict(p))


def completeness(p: ArtisanProfile) -> tuple[int, list[str]]:
    checks = [
        (15, bool(p.profile_image), "Add a profile photo"),
        (10, bool(p.headline), "Write a short headline"),
        (20, bool(p.bio and len(p.bio) >= 50), "Describe your experience (at least 50 characters)"),
        (15, p.price_min is not None, "Add your prices"),
        (15, len(p.locations) > 0, "Add the areas you work in"),
        (10, bool(p.whatsapp_number), "Add your WhatsApp number"),
        (15, len(p.portfolio) > 0, "Upload photos of your work"),
    ]
    score = sum(w for w, ok, _ in checks if ok)
    return score, [msg for _, ok, msg in checks if not ok]


def to_my_profile(p: ArtisanProfile) -> MyProfileOut:
    score, missing = completeness(p)
    return MyProfileOut(**to_detail_dict(p), category_id=p.category_id, whatsapp_number=p.whatsapp_number,
                        completeness=score, missing=missing, portfolio_limit=portfolio_limit(p.plan))


def is_verified(p: ArtisanProfile) -> bool:
    return p.verification_status == VerificationStatus.approved
