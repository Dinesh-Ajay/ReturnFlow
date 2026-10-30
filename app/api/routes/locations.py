from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.location import Location
from app.schemas.entities import LocationCreate, LocationResponse

router = APIRouter(prefix="/api/locations", tags=["Locations"])

@router.get("", response_model=List[LocationResponse])
def list_locations(
    location_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Location).filter(Location.active == True)
    if location_type:
        query = query.filter(Location.location_type == location_type)
    return query.order_by(Location.location_name.asc()).all()

@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    existing = db.query(Location).filter(Location.location_code == payload.location_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Location code {payload.location_code} already exists.")

    loc = Location(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc
