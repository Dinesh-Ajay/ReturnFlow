from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.owner import Owner
from app.schemas.entities import OwnerCreate, OwnerResponse

router = APIRouter(prefix="/api/owners", tags=["Owners"])

@router.get("", response_model=List[OwnerResponse])
def list_owners(
    owner_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Owner).filter(Owner.active == True)
    if owner_type:
        query = query.filter(Owner.owner_type == owner_type)
    return query.order_by(Owner.owner_name.asc()).all()

@router.post("", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
def create_owner(payload: OwnerCreate, db: Session = Depends(get_db)):
    existing = db.query(Owner).filter(Owner.owner_code == payload.owner_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Owner code {payload.owner_code} already exists.")

    owner = Owner(**payload.model_dump())
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner
