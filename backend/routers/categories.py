from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import ServiceCategory
from schemas import CategoryOut

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(ServiceCategory).filter(ServiceCategory.is_active.is_(True)).order_by(ServiceCategory.name).all()
