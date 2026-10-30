from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.asset_type import AssetType
from app.schemas.entities import AssetTypeCreate, AssetTypeResponse

router = APIRouter(prefix="/api/asset-types", tags=["Asset Types"])

@router.get("", response_model=List[AssetTypeResponse])
def list_asset_types(db: Session = Depends(get_db)):
    return db.query(AssetType).filter(AssetType.active == True).all()

@router.post("", response_model=AssetTypeResponse, status_code=status.HTTP_201_CREATED)
def create_asset_type(payload: AssetTypeCreate, db: Session = Depends(get_db)):
    existing = db.query(AssetType).filter(AssetType.type_code == payload.type_code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Asset type code {payload.type_code} already exists.")

    at = AssetType(**payload.model_dump())
    db.add(at)
    db.commit()
    db.refresh(at)
    return at
